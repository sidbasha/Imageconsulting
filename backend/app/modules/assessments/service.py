import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.integrations.storage import Storage
from app.modules.ai_analysis.service import latest_for_questionnaire
from app.modules.assessments import content
from app.modules.assessments.models import Assessment, AssessmentImage, Question, QuestionOption, Questionnaire, ResultProfile
from app.modules.auth.models import User
from app.modules.image_processing import quality

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg": "jpg", "image/png": "png"}
IMAGE_KINDS = ("face", "full_body")


def tr(text: dict | None, language: str):
    """Pick a language from a {"en": ..., "ar": ...} value, falling back to English."""
    if not text:
        return None
    return text.get(language) or text.get("en")


def seed_content(db: Session) -> None:
    """Adds questionnaires that do not exist yet. Existing ones are never
    overwritten: once seeded, content belongs to the admin panel."""
    existing = set(db.scalars(select(Questionnaire.key)))
    for order, spec in enumerate(content.QUESTIONNAIRES):
        if spec["key"] in existing:
            continue
        questionnaire = Questionnaire(
            key=spec["key"], feature_key=spec["feature"], title=spec["title"], intro=spec["intro"], sort_order=order
        )
        for q_order, (q_key, prompt, options) in enumerate(spec["questions"]):
            question = Question(key=q_key, prompt=prompt, sort_order=q_order)
            question.options = [
                QuestionOption(key=o_key, label=label, scores=scores, sort_order=i)
                for i, (o_key, label, scores) in enumerate(options)
            ]
            questionnaire.questions.append(question)
        for p_order, (p_key, title, summary, advice, *palette) in enumerate(spec["profiles"]):
            questionnaire.profiles.append(
                ResultProfile(
                    key=p_key, title=title, summary=summary, advice=advice,
                    palette=palette[0] if palette else None, sort_order=p_order,
                )
            )
        db.add(questionnaire)
    db.flush()


def get_questionnaire(db: Session, key: str, enabled: set[str]) -> Questionnaire:
    questionnaire = db.execute(
        select(Questionnaire).where(Questionnaire.key == key, Questionnaire.is_active)
    ).scalar_one_or_none()
    if questionnaire is None:
        raise AppError(404, "not_found")
    if questionnaire.feature_key not in enabled:
        raise AppError(404, "feature_not_available")
    return questionnaire


def latest(db: Session, user: User, questionnaire: Questionnaire) -> Assessment | None:
    return db.scalars(
        select(Assessment)
        .where(Assessment.user_id == user.id, Assessment.questionnaire_id == questionnaire.id)
        .order_by(Assessment.created_at.desc(), Assessment.id.desc())
        .limit(1)
    ).first()


def score(questionnaire: Questionnaire, answers: dict[str, str]) -> tuple[dict[str, float], str | None]:
    """Validates a complete answer set and returns (totals per profile, winning profile)."""
    expected = {q.key for q in questionnaire.questions}
    problems = {"missing": sorted(expected - answers.keys()), "unknown": sorted(answers.keys() - expected)}
    totals = {p.key: 0.0 for p in questionnaire.profiles}
    invalid = []
    for question in questionnaire.questions:
        chosen = next((o for o in question.options if o.key == answers.get(question.key)), None)
        if chosen is None:
            if question.key in answers:
                invalid.append(question.key)
            continue
        for profile_key, weight in chosen.scores.items():
            if profile_key in totals:
                totals[profile_key] += float(weight)
    if problems["missing"] or problems["unknown"] or invalid:
        raise AppError(422, "invalid_answers", {**problems, "invalid_option": invalid})
    # max() keeps the first of equal totals, i.e. the profile listed first.
    winner = max(totals, key=totals.get) if totals else None
    return totals, winner


def submit(db: Session, user: User, questionnaire: Questionnaire, answers: dict[str, str]) -> Assessment:
    totals, winner = score(questionnaire, answers)
    assessment = Assessment(
        user_id=user.id, questionnaire_id=questionnaire.id, answers=answers, scores=totals, profile_key=winner
    )
    db.add(assessment)
    db.flush()
    db.refresh(assessment)
    from app.modules.rewards.service import award  # late import: rewards depends on commerce

    award(db, user.id, "assessment_completed", ref=questionnaire.key)
    return assessment


def describe_questionnaire(questionnaire: Questionnaire, language: str) -> dict:
    return {
        "key": questionnaire.key,
        "title": tr(questionnaire.title, language),
        "intro": tr(questionnaire.intro, language),
        "questions": [
            {
                "key": q.key,
                "prompt": tr(q.prompt, language),
                "options": [{"key": o.key, "label": tr(o.label, language)} for o in q.options],
            }
            for q in questionnaire.questions
        ],
    }


def describe_result(questionnaire: Questionnaire, assessment: Assessment, language: str) -> dict:
    profile = next((p for p in questionnaire.profiles if p.key == assessment.profile_key), None)
    labels = {q.key: (tr(q.prompt, language), {o.key: tr(o.label, language) for o in q.options}) for q in questionnaire.questions}
    return {
        "questionnaire": questionnaire.key,
        "title": tr(questionnaire.title, language),
        "completed_at": assessment.created_at,
        # Self-assessed and rule-based: say so wherever the result is shown.
        "basis": "self_assessment",
        "profile": profile
        and {
            "key": profile.key,
            "title": tr(profile.title, language),
            "summary": tr(profile.summary, language),
            "palette": profile.palette,
            "advice": {category: tr(items, language) for category, items in profile.advice.items()},
        },
        "answers": [
            {"question": labels[key][0], "answer": labels[key][1].get(option)}
            for key, option in assessment.answers.items()
            if key in labels
        ],
    }


def recommendations(db: Session, user: User, category: str, enabled: set[str], language: str) -> dict:
    if category not in content.RECOMMENDATION_CATEGORIES:
        raise AppError(404, "not_found")
    feature, sources = content.RECOMMENDATION_CATEGORIES[category]
    if feature not in enabled:
        raise AppError(404, "feature_not_available")
    sections, missing = [], []
    for key in sources:
        questionnaire = db.execute(select(Questionnaire).where(Questionnaire.key == key)).scalar_one_or_none()
        if questionnaire is None or not questionnaire.is_active or questionnaire.feature_key not in enabled:
            continue
        assessment = latest(db, user, questionnaire)
        profile_key, basis = assessment and assessment.profile_key, "self_assessment"
        # A photo analysis newer than the questionnaire answer takes its place.
        analysed = latest_for_questionnaire(db, user, questionnaire.key)
        if analysed and (assessment is None or analysed.created_at > assessment.created_at):
            profile_key, basis = analysed.profile_key, "photo_analysis"
        profile = profile_key and next((p for p in questionnaire.profiles if p.key == profile_key), None)
        if not profile:
            missing.append({"key": questionnaire.key, "title": tr(questionnaire.title, language)})
            continue
        items = tr(profile.advice.get(category), language)
        if items:
            sections.append(
                {
                    "source": questionnaire.key,
                    "source_title": tr(questionnaire.title, language),
                    "basis": basis,
                    "result": tr(profile.title, language),
                    "palette": profile.palette,
                    "items": items,
                }
            )
    return {"category": category, "sections": sections, "missing": missing}


def store_image(
    db: Session, storage: Storage, user: User, *, data: bytes, content_type: str, kind: str, consent: bool
) -> AssessmentImage:
    if not consent:
        raise AppError(422, "consent_required")
    if kind not in IMAGE_KINDS:
        raise AppError(422, "invalid_image_kind")
    if content_type not in ALLOWED_TYPES:
        raise AppError(415, "unsupported_image_type")
    if len(data) > MAX_UPLOAD_BYTES:
        raise AppError(413, "image_too_large")
    report = quality.check(data, kind)
    if not report.ok:
        raise AppError(422, "photo_rejected", {"reasons": report.reasons, "measurements": report.measurements()})

    image = AssessmentImage(
        id=uuid.uuid4(),
        user_id=user.id,
        kind=kind,
        content_type=content_type,
        size_bytes=len(data),
        width=report.width,
        height=report.height,
        sha256=hashlib.sha256(data).hexdigest(),
        quality=report.measurements(),
        consent_at=datetime.now(UTC),
    )
    # Random key under the user's folder: not guessable, and never a user-supplied name.
    image.storage_key = f"assessment-images/{user.id}/{image.id}.{ALLOWED_TYPES[content_type]}"
    storage.put(image.storage_key, data)
    db.add(image)
    db.flush()
    return image


def list_images(db: Session, user: User) -> list[AssessmentImage]:
    return list(
        db.scalars(
            select(AssessmentImage)
            .where(AssessmentImage.user_id == user.id, AssessmentImage.deleted_at.is_(None))
            .order_by(AssessmentImage.created_at.desc())
        )
    )


def delete_image(db: Session, storage: Storage, user: User, image_id: uuid.UUID) -> None:
    """The user's retention control: removes the file and marks the record."""
    image = db.get(AssessmentImage, image_id)
    if image is None or image.user_id != user.id or image.deleted_at is not None:
        raise AppError(404, "not_found")
    storage.delete(image.storage_key)
    image.deleted_at = datetime.now(UTC)
    db.flush()
