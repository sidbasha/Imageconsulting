"""Consultations, audits, expert reports and the consultant colour workspace (rows 20-29, 56)."""

import re
import uuid
from datetime import UTC, datetime

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.integrations import pdf
from app.integrations.storage import Storage
from app.modules.ai_analysis import engine
from app.modules.assessments.models import AssessmentImage
from app.modules.assessments.service import tr
from app.modules.auth.models import User
from app.modules.commerce import service as commerce
from app.modules.commerce.documents import user_results
from app.modules.consultations import templates
from app.modules.consultations.models import Consultation, ConsultationFile, ExpertReport, ReportTemplate, WorkspaceAccess
from app.modules.marketplace.models import Booking, StylistProfile
from app.modules.platform import service as platform

FILE_TYPES = {"image/jpeg": "jpg", "image/png": "png"}
MAX_FILE_BYTES = 10 * 1024 * 1024
PURPOSES = {
    # service kind -> photo purposes the customer may add
    "consultation": ("outfit", "face"),
    "occasion_audit": ("outfit",),
    "wardrobe_audit": ("wardrobe",),
    "makeup_audit": ("product", "face"),
    "expert_color": ("face",),
    "personal_shopper_day": ("outfit", "wardrobe"),
}
INTAKE_REQUIRED = {
    "occasion_audit": ("occasion", "role", "personality"),  # row 21
    "wardrobe_audit": ("goals",),
}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def seed(db: Session) -> None:
    have = set(db.scalars(select(ReportTemplate.key)))
    for spec in templates.TEMPLATES:
        if spec["key"] not in have:
            db.add(ReportTemplate(**spec))
    db.flush()


def open_for_booking(db: Session, booking: Booking) -> Consultation:
    existing = db.execute(select(Consultation).where(Consultation.booking_id == booking.id)).scalar_one_or_none()
    if existing:
        return existing
    consultation = Consultation(booking_id=booking.id, customer_id=booking.customer_id, profile_id=booking.profile_id,
                                kind=booking.kind, intake={})
    db.add(consultation)
    db.flush()
    return consultation


def for_party(db: Session, user: User, consultation_id: uuid.UUID) -> tuple[Consultation, str]:
    """The consultation and whether the user is its "customer" or "stylist"."""
    consultation = db.get(Consultation, consultation_id)
    if consultation is None:
        raise AppError(404, "not_found")
    if consultation.customer_id == user.id:
        return consultation, "customer"
    profile = db.get(StylistProfile, consultation.profile_id)
    if profile.user_id == user.id:
        return consultation, "stylist"
    raise AppError(404, "not_found")


def require_active(db: Session, consultation: Consultation) -> Booking:
    booking = db.get(Booking, consultation.booking_id)
    if booking.status not in ("confirmed", "completed"):
        raise AppError(409, "booking_not_confirmed")
    return booking


def set_intake(db: Session, consultation: Consultation, intake: dict) -> Consultation:
    missing = [k for k in INTAKE_REQUIRED.get(consultation.kind, ()) if not str(intake.get(k, "")).strip()]
    if missing:
        raise AppError(422, "intake_incomplete", {"missing": missing})
    consultation.intake = {k: str(v)[:1000] for k, v in intake.items()}
    db.flush()
    return consultation


def add_file(db: Session, storage: Storage, user: User, consultation: Consultation, *, purpose: str, data: bytes,
             content_type: str, caption: str | None, consent: bool) -> ConsultationFile:
    if not consent:
        raise AppError(422, "consent_required")
    if purpose not in PURPOSES.get(consultation.kind, ()):
        raise AppError(422, "invalid_file_purpose", {"allowed": list(PURPOSES.get(consultation.kind, ()))})
    if consultation.kind == "makeup_audit" and purpose == "product":
        # Row 23 note: makeup audit requires a completed seasonal colour analysis.
        if not user_results(db, user).get("seasonal_color", {}).get("profile"):
            raise AppError(409, "seasonal_color_required")
    if content_type not in FILE_TYPES:
        raise AppError(415, "unsupported_image_type")
    if len(data) > MAX_FILE_BYTES:
        raise AppError(413, "image_too_large")
    item = ConsultationFile(id=uuid.uuid4(), consultation_id=consultation.id, purpose=purpose, content_type=content_type,
                            caption=caption, consent_at=datetime.now(UTC))
    item.storage_key = f"consultations/{consultation.id}/{item.id}.{FILE_TYPES[content_type]}"
    storage.put(item.storage_key, data)
    db.add(item)
    db.flush()
    return item


def share_photo(db: Session, storage: Storage, user: User, consultation: Consultation, image_id: uuid.UUID, consent: bool) -> ConsultationFile:
    """The customer shares one of her assessment photos with this stylist."""
    image = db.get(AssessmentImage, image_id)
    if image is None or image.user_id != user.id or image.deleted_at is not None:
        raise AppError(404, "not_found")
    purpose = "face" if image.kind == "face" else "outfit"
    return add_file(db, storage, user, consultation, purpose=purpose, data=storage.get(image.storage_key),
                    content_type=image.content_type, caption=None, consent=consent)


VERDICTS = ("suits", "adjust", "avoid")


def set_verdict(db: Session, consultation: Consultation, file_id: uuid.UUID, verdict: str, note: str | None) -> ConsultationFile:
    item = db.get(ConsultationFile, file_id)
    if item is None or item.consultation_id != consultation.id:
        raise AppError(404, "not_found")
    if verdict not in VERDICTS:
        raise AppError(422, "invalid_verdict")
    item.verdict = {"verdict": verdict, "note": note}
    db.flush()
    return item


# ---------------------------------------------------------------- reports (25, 56)

def template_for(db: Session, kind: str) -> ReportTemplate:
    template = db.execute(select(ReportTemplate).where(ReportTemplate.service_kind == kind, ReportTemplate.is_active)
                          .order_by(ReportTemplate.created_at)).scalars().first()
    if template is None:
        raise AppError(409, "no_report_template")
    return template


def validate_content(template: ReportTemplate, content: dict, final: bool) -> dict:
    """Keeps only known sections and checks each value against its type."""
    clean, problems = {}, {}
    for section in template.sections:
        key, kind = section["key"], section["type"]
        value = content.get(key)
        if value in (None, "", []):
            if final and section.get("required"):
                problems[key] = "required"
            continue
        if kind in ("decision", "choice"):
            ok = value in section.get("options", [])
        elif kind == "text":
            ok = isinstance(value, str) and len(value) <= 8000
        elif kind == "list":
            ok = isinstance(value, list) and all(isinstance(v, str) and len(v) <= 500 for v in value) and len(value) <= 40
        elif kind == "palette":
            ok = isinstance(value, list) and 1 <= len(value) <= 24 and all(isinstance(v, str) and HEX.match(v) for v in value)
        else:
            ok = False
        if ok:
            clean[key] = value
        else:
            problems[key] = "invalid"
    if problems:
        raise AppError(422, "invalid_report", problems)
    return clean


def save_report(db: Session, consultation: Consultation, content: dict) -> ExpertReport:
    report = db.execute(select(ExpertReport).where(ExpertReport.consultation_id == consultation.id)).scalar_one_or_none()
    if report and report.status == "delivered":
        raise AppError(409, "report_already_delivered")
    template = db.get(ReportTemplate, report.template_id) if report else template_for(db, consultation.kind)
    clean = validate_content(template, content, final=False)
    if report is None:
        report = ExpertReport(consultation_id=consultation.id, template_id=template.id, content=clean)
        db.add(report)
    else:
        report.content = clean
    db.flush()
    return report


def deliver_report(db: Session, consultation: Consultation) -> ExpertReport:
    report = db.execute(select(ExpertReport).where(ExpertReport.consultation_id == consultation.id)).scalar_one_or_none()
    if report is None:
        raise AppError(409, "report_missing")
    if report.status == "delivered":
        raise AppError(409, "report_already_delivered")
    validate_content(db.get(ReportTemplate, report.template_id), report.content, final=True)
    report.status, report.delivered_at = "delivered", datetime.now(UTC)
    consultation.status = "delivered"
    db.flush()
    return report


def describe_report(db: Session, report: ExpertReport, language: str) -> dict:
    template = db.get(ReportTemplate, report.template_id)
    sections = []
    for section in template.sections:
        value = report.content.get(section["key"])
        if value in (None, "", []):
            continue
        if section["type"] in ("decision", "choice"):
            value = {"key": value, "label": tr(templates.OPTION_LABELS.get(value), language) or value}
        sections.append({"key": section["key"], "title": tr(section["title"], language), "type": section["type"], "value": value})
    return {"template": template.key, "title": tr(template.title, language), "status": report.status,
            "delivered_at": report.delivered_at, "sections": sections}


def report_pdf(db: Session, consultation: Consultation, report: ExpertReport, language: str) -> bytes:
    described = describe_report(db, report, language)
    profile = db.get(StylistProfile, consultation.profile_id)
    customer = db.get(User, consultation.customer_id)
    files = db.scalars(select(ConsultationFile).where(ConsultationFile.consultation_id == consultation.id,
                                                      ConsultationFile.verdict.is_not(None))).all()
    sections = []
    for s in described["sections"]:
        value = s["value"]
        if s["type"] in ("decision", "choice"):
            sections.append(pdf.Section(heading=s["title"], paragraphs=[value["label"]]))
        elif s["type"] == "text":
            sections.append(pdf.Section(heading=s["title"], paragraphs=[value]))
        elif s["type"] == "list":
            sections.append(pdf.Section(heading=s["title"], bullets=value))
        elif s["type"] == "palette":
            sections.append(pdf.Section(heading=s["title"], palette=value))
    if files:
        heading = {"en": "Items reviewed", "ar": "العناصر التي تمّت مراجعتها"}[language]
        verdicts = {"suits": {"en": "Suits you", "ar": "يناسبك"}, "adjust": {"en": "Use with changes", "ar": "استخدميه مع تعديل"},
                    "avoid": {"en": "Avoid", "ar": "تجنّبيه"}}
        rows = [(f.caption or f.purpose, f"{verdicts[f.verdict['verdict']][language]}"
                 + (f" ({f.verdict['note']})" if f.verdict.get("note") else "")) for f in files]
        sections.append(pdf.Section(heading=heading, rows=rows))
    subtitle = {"en": f"Prepared by {profile.display_name} for {customer.full_name}",
                "ar": f"أعدّته {profile.display_name} لـ {customer.full_name}"}[language]
    footer = {"en": "Expert assessment by the named consultant.", "ar": "تقييم من الخبيرة المذكورة."}[language]
    return pdf.build(title=described["title"], subtitle=subtitle, sections=sections, language=language, footer=footer)


# ---------------------------------------------------------------- workspace (27-29)

def open_workspace(db: Session, stylist: User, consultation: Consultation, enabled: set[str]) -> WorkspaceAccess:
    profile = db.get(StylistProfile, consultation.profile_id)
    access = db.execute(select(WorkspaceAccess).where(
        WorkspaceAccess.profile_id == profile.id, WorkspaceAccess.customer_id == consultation.customer_id)).scalar_one_or_none()
    if access:
        return access  # already paid for this client
    used = 0
    if "phase2.metered_tool_access" in enabled:
        used = platform.get(db, "workspace.credits_per_client")
        commerce.consume_credit(db, stylist, "workspace.credits", used)
    access = WorkspaceAccess(profile_id=profile.id, customer_id=consultation.customer_id, credits_used=used)
    db.add(access)
    db.flush()
    return access


def require_workspace(db: Session, consultation: Consultation) -> None:
    if not db.execute(select(WorkspaceAccess.id).where(
            WorkspaceAccess.profile_id == consultation.profile_id,
            WorkspaceAccess.customer_id == consultation.customer_id)).first():
        raise AppError(409, "workspace_not_open")


def face_photo(db: Session, storage: Storage, consultation: Consultation, file_id: uuid.UUID) -> np.ndarray:
    item = db.get(ConsultationFile, file_id)
    if item is None or item.consultation_id != consultation.id or item.purpose != "face":
        raise AppError(404, "not_found")
    return engine.decode(storage.get(item.storage_key))
