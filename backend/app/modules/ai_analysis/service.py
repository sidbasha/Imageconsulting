import uuid

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.integrations.storage import Storage
from app.modules.ai_analysis import colour_types, engine
from app.modules.ai_analysis.colour import analyse_colour
from app.modules.ai_analysis.models import PhotoAnalysis
from app.modules.ai_analysis.shapes import Unusable, analyse_body_shape, analyse_face_shape
from app.modules.assessments.models import AssessmentImage, Questionnaire
from app.modules.auth.models import User

# kind -> (feature switch, photo kind it needs, analyser, questionnaire whose result profiles it shares)
KINDS = {
    "face_shape": ("phase1.face_shape", "face", analyse_face_shape, "face_shape"),
    "body_shape": ("phase1.body_shape", "full_body", analyse_body_shape, "body_shape"),
    "seasonal_color": ("phase1.seasonal_color", "face", analyse_colour, "seasonal_color"),
}


def kind_spec(kind: str, enabled: set[str]):
    if kind not in KINDS:
        raise AppError(404, "not_found")
    if KINDS[kind][0] not in enabled or "phase1.photo_assessment" not in enabled:
        raise AppError(404, "feature_not_available")
    return KINDS[kind]


def user_image(db: Session, user: User, image_id: uuid.UUID) -> AssessmentImage:
    image = db.get(AssessmentImage, image_id)
    if image is None or image.user_id != user.id or image.deleted_at is not None:
        raise AppError(404, "not_found")
    return image


def load_rgb(storage: Storage, image: AssessmentImage) -> np.ndarray:
    return engine.decode(storage.get(image.storage_key))


def run(db: Session, storage: Storage, user: User, kind: str, image_id: uuid.UUID, enabled: set[str]) -> PhotoAnalysis:
    _, photo_kind, analyse, _ = kind_spec(kind, enabled)
    image = user_image(db, user, image_id)
    if image.kind != photo_kind:
        raise AppError(422, "wrong_photo_kind", {"needs": photo_kind})
    try:
        result = analyse(load_rgb(storage, image))
    except FileNotFoundError as exc:
        raise AppError(404, "photo_missing") from exc
    except engine.ModelsMissing as exc:
        raise AppError(503, "analysis_unavailable") from exc
    except Unusable as exc:
        raise AppError(422, "photo_not_analysable", {"reasons": exc.reasons, "measurements": exc.measurements}) from exc
    details = {}
    if hasattr(result, "axes"):
        type_scores = colour_types.scores(result.axes)
        details = {"axes": result.axes, "swatches": result.swatches, "colour_type": next(iter(type_scores)),
                   # A list, not a dict: JSONB does not keep key order.
                   "type_scores": [[k, v] for k, v in list(type_scores.items())[:3]]}
    analysis = PhotoAnalysis(
        user_id=user.id,
        image_id=image.id,
        kind=kind,
        profile_key=result.profile_key,
        confidence=result.confidence,
        scores=result.scores,
        measurements=result.measurements,
        details=details,
        notes=result.notes,
        model_version=engine.MODEL_VERSION,
    )
    db.add(analysis)
    db.flush()
    db.refresh(analysis)
    from app.modules.rewards.service import award

    award(db, user.id, "photo_analysis", ref=kind)
    return analysis


def latest(db: Session, user: User, kind: str) -> PhotoAnalysis | None:
    return db.scalars(
        select(PhotoAnalysis)
        .where(PhotoAnalysis.user_id == user.id, PhotoAnalysis.kind == kind)
        .order_by(PhotoAnalysis.created_at.desc(), PhotoAnalysis.id.desc())
        .limit(1)
    ).first()


def latest_for_questionnaire(db: Session, user: User, questionnaire_key: str) -> PhotoAnalysis | None:
    for kind, (*_, source) in KINDS.items():
        if source == questionnaire_key:
            return latest(db, user, kind)
    return None


def describe(db: Session, analysis: PhotoAnalysis, language: str) -> dict:
    from app.modules.assessments.service import tr

    questionnaire = db.execute(
        select(Questionnaire).where(Questionnaire.key == KINDS[analysis.kind][3])
    ).scalar_one_or_none()
    profiles = {p.key: p for p in questionnaire.profiles} if questionnaire else {}
    profile = profiles.get(analysis.profile_key)
    return {
        "id": analysis.id,
        "kind": analysis.kind,
        "image_id": analysis.image_id,  # None once the photo was deleted; the result is kept
        "basis": "photo_analysis",
        # Indicative only; expert analysis is a separate, consultant-made result.
        "indicative": True,
        "created_at": analysis.created_at,
        "confidence": analysis.confidence,
        "low_confidence": "low_confidence" in analysis.notes,
        "notes": analysis.notes,
        "scores": [
            {"key": key, "title": tr(profiles[key].title, language) if key in profiles else key, "score": score}
            for key, score in sorted(analysis.scores.items(), key=lambda kv: -kv[1])
        ],
        "measurements": analysis.measurements,
        **{k: v for k, v in (analysis.details or {}).items() if k in ("axes", "swatches")},
        "profile": profile
        and {
            "key": profile.key,
            "title": tr(profile.title, language),
            "summary": tr(profile.summary, language),
            "palette": profile.palette,
            "advice": {category: tr(items, language) for category, items in profile.advice.items()},
        },
        "colour_type": _colour_type(analysis, language),
        "model_version": analysis.model_version,
    }


def _colour_type(analysis: PhotoAnalysis, language: str) -> dict | None:
    """The twelve-type reading of a colour analysis (older results: derived from their stored axes)."""
    from app.modules.assessments.service import tr

    axes = (analysis.details or {}).get("axes")
    if analysis.kind != "seasonal_color" or not axes:
        return None
    key = analysis.details.get("colour_type") or colour_types.nearest(axes)
    pairs = analysis.details.get("type_scores") or list(colour_types.scores(axes).items())[:3]
    pairs = sorted(((k, v) for k, v in pairs), key=lambda kv: -kv[1])
    return {**colour_types.summary(key, language),
            "scores": [{"key": k, "title": tr(colour_types.BY_KEY[k].title, language), "score": v} for k, v in pairs]}
