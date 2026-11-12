import uuid

import numpy as np
from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.core.errors import AppError, pick_language
from app.database.session import get_db
from app.integrations.storage import Storage, get_storage
from app.modules.ai_analysis import engine, previews
from app.modules.ai_analysis.colour import analyse_colour
from app.modules.ai_analysis.shapes import Unusable
from app.modules.auth.models import User
from app.modules.consultations import service
from app.modules.consultations.models import Consultation, ConsultationFile, ExpertReport, ReportTemplate
from app.modules.feature_flags.guard import enabled_features, require_feature
from app.modules.marketplace.models import StylistProfile
from app.modules.marketplace.service import SERVICE_FEATURES

router = APIRouter(prefix="/consultations", tags=["consultations"], dependencies=[Depends(require_feature("phase2.consultations"))])


def _party(consultation_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db),
           on: set[str] = Depends(enabled_features)) -> tuple[Consultation, str]:
    consultation, role = service.for_party(db, user, consultation_id)
    if SERVICE_FEATURES.get(consultation.kind) not in on:
        raise AppError(404, "feature_not_available")
    return consultation, role


def _stylist(party=Depends(_party)) -> Consultation:
    consultation, role = party
    if role != "stylist":
        raise AppError(403, "permission_denied")
    return consultation


def _customer(party=Depends(_party)) -> Consultation:
    consultation, role = party
    if role != "customer":
        raise AppError(403, "permission_denied")
    return consultation


def file_out(f: ConsultationFile) -> dict:
    return {"id": f.id, "purpose": f.purpose, "caption": f.caption, "verdict": f.verdict, "created_at": f.created_at}


def consultation_out(db: Session, c: Consultation, role: str, language: str) -> dict:
    report = db.execute(select(ExpertReport).where(ExpertReport.consultation_id == c.id)).scalar_one_or_none()
    files = db.scalars(select(ConsultationFile).where(ConsultationFile.consultation_id == c.id).order_by(ConsultationFile.created_at))
    profile = db.get(StylistProfile, c.profile_id)
    # The customer sees the report only once delivered.
    visible = report and (role == "stylist" or report.status == "delivered")
    return {"id": c.id, "booking_id": c.booking_id, "kind": c.kind, "status": c.status, "intake": c.intake,
            "role": role, "stylist": {"id": profile.id, "display_name": profile.display_name},
            "files": [file_out(f) for f in files],
            "report": service.describe_report(db, report, language) if visible else None,
            "required_intake": list(service.INTAKE_REQUIRED.get(c.kind, ())),
            "allowed_purposes": list(service.PURPOSES.get(c.kind, ()))}


@router.get("")
def mine(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    language = pick_language(request)
    profile = db.execute(select(StylistProfile).where(StylistProfile.user_id == user.id)).scalar_one_or_none()
    rows = list(db.scalars(select(Consultation).where(Consultation.customer_id == user.id)))
    if profile:
        rows += list(db.scalars(select(Consultation).where(Consultation.profile_id == profile.id)))
    return [consultation_out(db, c, "customer" if c.customer_id == user.id else "stylist", language)
            for c in sorted(rows, key=lambda c: c.created_at, reverse=True)]


@router.get("/{consultation_id}")
def one(request: Request, party=Depends(_party), db: Session = Depends(get_db)) -> dict:
    consultation, role = party
    return consultation_out(db, consultation, role, pick_language(request))


class IntakeIn(BaseModel):
    intake: dict[str, str]


@router.put("/{consultation_id}/intake")
def intake(body: IntakeIn, request: Request, consultation: Consultation = Depends(_customer), db: Session = Depends(get_db)) -> dict:
    service.require_active(db, consultation)
    service.set_intake(db, consultation, body.intake)
    return consultation_out(db, consultation, "customer", pick_language(request))


@router.post("/{consultation_id}/files", status_code=status.HTTP_201_CREATED)
async def upload(
    purpose: str = Form(...), consent: bool = Form(...), caption: str | None = Form(default=None, max_length=300),
    file: UploadFile = File(...), consultation: Consultation = Depends(_customer), user: User = Depends(get_current_user),
    db: Session = Depends(get_db), storage: Storage = Depends(get_storage),
) -> dict:
    service.require_active(db, consultation)
    data = await file.read(service.MAX_FILE_BYTES + 1)
    return file_out(service.add_file(db, storage, user, consultation, purpose=purpose, data=data,
                                     content_type=file.content_type or "", caption=caption, consent=consent))


class ShareIn(BaseModel):
    image_id: uuid.UUID
    consent: bool


@router.post("/{consultation_id}/share-photo", status_code=status.HTTP_201_CREATED)
def share(body: ShareIn, consultation: Consultation = Depends(_customer), user: User = Depends(get_current_user),
          db: Session = Depends(get_db), storage: Storage = Depends(get_storage)) -> dict:
    service.require_active(db, consultation)
    return file_out(service.share_photo(db, storage, user, consultation, body.image_id, body.consent))


@router.get("/{consultation_id}/files/{file_id}")
def file_content(file_id: uuid.UUID, party=Depends(_party), db: Session = Depends(get_db), storage: Storage = Depends(get_storage)) -> Response:
    consultation, _ = party
    item = db.get(ConsultationFile, file_id)
    if item is None or item.consultation_id != consultation.id:
        raise AppError(404, "not_found")
    return Response(storage.get(item.storage_key), media_type=item.content_type, headers={"Cache-Control": "no-store"})


class VerdictIn(BaseModel):
    verdict: str = Field(pattern="^(suits|adjust|avoid)$")
    note: str | None = Field(default=None, max_length=300)


@router.put("/{consultation_id}/files/{file_id}/verdict")
def verdict(file_id: uuid.UUID, body: VerdictIn, consultation: Consultation = Depends(_stylist), db: Session = Depends(get_db)) -> dict:
    return file_out(service.set_verdict(db, consultation, file_id, body.verdict, body.note))


@router.post("/{consultation_id}/files/{file_id}/recognise", dependencies=[Depends(require_feature("phase2.product_recognition"))])
def recognise(file_id: uuid.UUID, consultation: Consultation = Depends(_stylist)) -> dict:
    """Row 26. Identifying a skincare or makeup product from a photo needs a
    product-recognition service and a product database; none is chosen, so this
    reports that plainly instead of guessing."""
    raise AppError(503, "integration_not_configured", {"integration": "product_recognition"})


@router.get("/{consultation_id}/call")
def call(party=Depends(_party)) -> dict:
    """Video sessions need a provider (for example Twilio, Agora, Daily); none is
    chosen. Consultations run through in-app messaging and reports meanwhile."""
    raise AppError(503, "integration_not_configured", {"integration": "video"})


class ReportIn(BaseModel):
    content: dict


@router.get("/{consultation_id}/report/template")
def report_template(request: Request, consultation: Consultation = Depends(_stylist), db: Session = Depends(get_db)) -> dict:
    from app.modules.assessments.service import tr

    language = pick_language(request)
    template = service.template_for(db, consultation.kind)
    return {"key": template.key, "title": tr(template.title, language), "sections": [
        {**s, "title": tr(s["title"], language)} for s in template.sections]}


@router.put("/{consultation_id}/report", dependencies=[Depends(require_feature("phase2.expert_reports"))])
def save_report(body: ReportIn, request: Request, consultation: Consultation = Depends(_stylist), db: Session = Depends(get_db)) -> dict:
    service.require_active(db, consultation)
    return service.describe_report(db, service.save_report(db, consultation, body.content), pick_language(request))


@router.post("/{consultation_id}/report/deliver", dependencies=[Depends(require_feature("phase2.expert_reports"))])
def deliver(request: Request, consultation: Consultation = Depends(_stylist), db: Session = Depends(get_db)) -> dict:
    return service.describe_report(db, service.deliver_report(db, consultation), pick_language(request))


@router.get("/{consultation_id}/report.pdf", dependencies=[Depends(require_feature("phase2.expert_reports"))])
def report_pdf(request: Request, party=Depends(_party), db: Session = Depends(get_db)) -> Response:
    consultation, role = party
    report = db.execute(select(ExpertReport).where(ExpertReport.consultation_id == consultation.id)).scalar_one_or_none()
    if report is None or (role == "customer" and report.status != "delivered"):
        raise AppError(404, "not_found")
    data = service.report_pdf(db, consultation, report, pick_language(request))
    return Response(data, media_type="application/pdf", headers={"Cache-Control": "no-store",
                    "Content-Disposition": f'attachment; filename="report-{consultation.id}.pdf"'})


# ---------------------------------------------------------------- consultant colour workspace (27-29)

workspace = APIRouter(prefix="/workspace", tags=["colour workspace"], dependencies=[Depends(require_feature("phase2.color_workspace"))])


@workspace.post("/{consultation_id}/open")
def open_workspace(consultation: Consultation = Depends(_stylist), user: User = Depends(get_current_user),
                   db: Session = Depends(get_db), on: set[str] = Depends(enabled_features)) -> dict:
    """Consultant-only (row 27). Uses credits once per client when metering is on (row 29)."""
    if not user.has_permission("stylist.practice"):
        raise AppError(403, "permission_denied")
    service.require_active(db, consultation)
    access = service.open_workspace(db, user, consultation, on)
    return {"open": True, "credits_used": access.credits_used}


def _render(db, storage, consultation, file_id, draw) -> Response:
    service.require_workspace(db, consultation)
    rgb = service.face_photo(db, storage, consultation, file_id)
    try:
        out = draw(rgb)
    except engine.ModelsMissing as exc:
        raise AppError(503, "analysis_unavailable") from exc
    except Unusable as exc:
        raise AppError(422, "photo_not_analysable", {"reasons": exc.reasons}) from exc
    return Response(engine.encode_jpeg(out), media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@workspace.get("/{consultation_id}/drape", dependencies=[Depends(require_feature("phase2.digital_draping"))])
def drape(file_id: uuid.UUID, colour: str = Query(pattern=r"^#[0-9a-fA-F]{6}$"), consultation: Consultation = Depends(_stylist),
          db: Session = Depends(get_db), storage: Storage = Depends(get_storage)) -> Response:
    """The client's face with one fabric colour draped below the chin (row 28)."""
    return _render(db, storage, consultation, file_id, lambda rgb: previews.drape(rgb, colour))


class CompareIn(BaseModel):
    file_id: uuid.UUID
    colours: list[str] = Field(min_length=2, max_length=8)


@workspace.post("/{consultation_id}/compare", dependencies=[Depends(require_feature("phase2.digital_draping"))])
def compare(body: CompareIn, consultation: Consultation = Depends(_stylist), db: Session = Depends(get_db),
            storage: Storage = Depends(get_storage)) -> Response:
    """Several drapes side by side, the way a consultant compares fabrics."""
    import cv2

    for colour in body.colours:
        if not previews.HEX.match(colour):
            raise AppError(422, "invalid_preview_request")

    def grid(rgb):
        tiles = [previews.drape(rgb, c) for c in body.colours]
        height = 420
        tiles = [cv2.resize(t, (int(t.shape[1] * height / t.shape[0]), height)) for t in tiles]
        rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
        width = max(r.shape[1] for r in rows)
        return np.vstack([np.pad(r, ((0, 0), (0, width - r.shape[1]), (0, 0)), constant_values=255) for r in rows])

    return _render(db, storage, consultation, body.file_id, grid)


@workspace.post("/{consultation_id}/indicative")
def indicative(file_id: uuid.UUID, consultation: Consultation = Depends(_stylist), db: Session = Depends(get_db),
               storage: Storage = Depends(get_storage)) -> dict:
    """The automated reading as a starting point for the consultant's own judgement."""
    service.require_workspace(db, consultation)
    try:
        result = analyse_colour(service.face_photo(db, storage, consultation, file_id))
    except Unusable as exc:
        raise AppError(422, "photo_not_analysable", {"reasons": exc.reasons}) from exc
    return {"indicative": True, "season": result.profile_key, "scores": result.scores, "axes": result.axes,
            "swatches": result.swatches, "notes": result.notes}


# ---------------------------------------------------------------- admin: report templates (56)

admin = APIRouter(prefix="/admin/report-templates", tags=["admin: report templates"])


class SectionIn(BaseModel):
    key: str = Field(pattern="^[a-z_]{2,40}$")
    title: dict[str, str]
    type: str = Field(pattern="^(decision|text|list|choice|palette)$")
    options: list[str] = []
    required: bool = False


class TemplateIn(BaseModel):
    title: dict[str, str]
    sections: list[SectionIn] = Field(min_length=1, max_length=40)
    is_active: bool = True
    content_status: str = Field(default="draft", pattern="^(draft|approved)$")


@admin.get("")
def templates_list(_: User = Depends(require_permission("content.manage")), db: Session = Depends(get_db)) -> list[dict]:
    return [{"key": t.key, "service_kind": t.service_kind, "title": t.title, "sections": t.sections,
             "is_active": t.is_active, "content_status": t.content_status} for t in db.scalars(select(ReportTemplate))]


@admin.put("/{key}")
def template_put(key: str, body: TemplateIn, _: User = Depends(require_permission("content.manage")), db: Session = Depends(get_db)) -> dict:
    template = db.execute(select(ReportTemplate).where(ReportTemplate.key == key)).scalar_one_or_none()
    if template is None:
        raise AppError(404, "not_found")
    if len({s.key for s in body.sections}) != len(body.sections):
        raise AppError(422, "invalid_report", {"sections": "duplicate keys"})
    for s in body.sections:
        if s.type in ("decision", "choice") and not s.options:
            raise AppError(422, "invalid_report", {s.key: "options required"})
    template.title, template.sections = body.title, [s.model_dump() for s in body.sections]
    template.is_active, template.content_status = body.is_active, body.content_status
    db.flush()
    return {"key": template.key}
