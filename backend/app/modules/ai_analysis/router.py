import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.errors import AppError, pick_language
from app.database.session import get_db
from app.integrations.storage import Storage, get_storage
from app.modules.ai_analysis import engine, previews, service
from app.modules.ai_analysis.shapes import Unusable
from app.modules.assessments.router import enabled
from app.modules.auth.models import User
from app.modules.feature_flags.guard import require_feature

router = APIRouter(prefix="/analysis", tags=["photo-analysis"])


class AnalyseIn(BaseModel):
    image_id: uuid.UUID


@router.post("/{kind}", status_code=status.HTTP_201_CREATED)
def analyse(
    kind: str,
    body: AnalyseIn,
    request: Request,
    on: set[str] = Depends(enabled),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> dict:
    """Analyse one of the user's photos: face_shape, body_shape or seasonal_color.
    The result is indicative and is labelled as automated photo analysis."""
    analysis = service.run(db, storage, user, kind, body.image_id, on)
    return service.describe(db, analysis, pick_language(request))


@router.get("/{kind}")
def latest(
    kind: str, request: Request, on: set[str] = Depends(enabled), user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict | None:
    service.kind_spec(kind, on)
    analysis = service.latest(db, user, kind)
    return analysis and service.describe(db, analysis, pick_language(request))


# ---------------------------------------------------------------- previews

HexColour = Field(pattern=r"^#[0-9a-fA-F]{6}$", examples=["#8b2e1a"])


class ColourIn(BaseModel):
    image_id: uuid.UUID
    colour: str = HexColour


class MakeupIn(BaseModel):
    image_id: uuid.UUID
    lip_colour: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    brow_colour: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    intensity: float = Field(default=0.7, ge=0.1, le=1.0)


def _render(db, storage, user, image_id, needs: str, draw) -> Response:
    image = service.user_image(db, user, image_id)
    if image.kind != needs:
        raise AppError(422, "wrong_photo_kind", {"needs": needs})
    try:
        out = draw(service.load_rgb(storage, image))
    except engine.ModelsMissing as exc:
        raise AppError(503, "analysis_unavailable") from exc
    except Unusable as exc:
        raise AppError(422, "photo_not_analysable", {"reasons": exc.reasons}) from exc
    except ValueError as exc:
        raise AppError(422, "invalid_preview_request", {"message": str(exc)}) from exc
    # Generated on request and never stored; tell caches the same.
    return Response(engine.encode_jpeg(out), media_type="image/jpeg", headers={"Cache-Control": "no-store"})


previews_router = APIRouter(prefix="/previews", tags=["previews"], dependencies=[Depends(require_feature("phase1.photo_assessment"))])


@previews_router.post("/hair-colour", dependencies=[Depends(require_feature("phase1.hair_preview"))], response_class=Response)
def hair_colour(body: ColourIn, user: User = Depends(get_current_user), db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    """Hair colour on the user's face photo (colour only, not a new cut)."""
    return _render(db, storage, user, body.image_id, "face", lambda rgb: previews.hair_colour(rgb, body.colour))


@previews_router.post("/outfit-colour", dependencies=[Depends(require_feature("phase1.virtual_tryon"))], response_class=Response)
def outfit_colour(body: ColourIn, user: User = Depends(get_current_user), db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    """The user's own clothes shown in another colour (colour try-on, not a garment try-on)."""
    return _render(db, storage, user, body.image_id, "full_body", lambda rgb: previews.outfit_colour(rgb, body.colour))


@previews_router.post("/makeup", dependencies=[Depends(require_feature("phase3.pmu_preview"))], response_class=Response)
def makeup(body: MakeupIn, user: User = Depends(get_current_user), db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    """Permanent-makeup preview: lip and brow colour."""
    return _render(
        db, storage, user, body.image_id, "face",
        lambda rgb: previews.makeup(rgb, body.lip_colour, body.brow_colour, body.intensity),
    )
