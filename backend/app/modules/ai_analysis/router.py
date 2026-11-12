import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.core.errors import AppError, pick_language
from app.database.session import get_db
from app.integrations.storage import Storage, get_storage
from app.modules.ai_analysis import colour_types, engine, previews, service, tryon
from app.modules.ai_analysis.models import TryOnItem
from app.modules.ai_analysis.shapes import Unusable
from app.modules.assessments.router import enabled
from app.modules.assessments.service import tr
from app.modules.auth.models import User
from app.modules.feature_flags.guard import require_feature
from app.modules.users.deps import eligible_user

router = APIRouter(prefix="/analysis", tags=["photo-analysis"], dependencies=[Depends(eligible_user)])


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


previews_router = APIRouter(prefix="/previews", tags=["previews"], dependencies=[Depends(require_feature("phase1.photo_assessment")), Depends(eligible_user)])


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


# ---------------------------------------------------------------- garment and hairstyle try-on (rows 11, 12)


TRYON_FEATURES = {"garment": "phase1.virtual_tryon", "hairstyle": "phase1.hair_preview"}
TRYON_NEEDS = {"garment": "full_body", "hairstyle": "face"}


def tryon_out(item: TryOnItem, language: str) -> dict:
    return {"id": item.id, "kind": item.kind, "title": tr(item.title, language), "category": item.category,
            "retail_item_id": item.retail_item_id}


catalogue = APIRouter(prefix="/tryon", tags=["try-on"], dependencies=[Depends(eligible_user)])


@catalogue.get("/items")
def tryon_items(
    request: Request, kind: str = Query(pattern="^(garment|hairstyle)$"), on: set[str] = Depends(enabled),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> list[dict]:
    """Approved items, the ones tagged for the user's own results first."""
    if TRYON_FEATURES[kind] not in on:
        raise AppError(404, "feature_not_available")
    from app.modules.commerce.documents import user_results

    mine = {k: r["profile"].key for k, r in user_results(db, user).items() if r["profile"]}
    items = db.scalars(select(TryOnItem).where(TryOnItem.kind == kind, TryOnItem.is_active, TryOnItem.content_status == "approved"))
    scored = sorted(items, key=lambda i: (-sum(mine.get(d) in v for d, v in i.tags.items()), tr(i.title, "en") or ""))
    language = pick_language(request)
    return [tryon_out(i, language) | {"suggested": any(mine.get(d) in v for d, v in i.tags.items())} for i in scored]


def _item(db: Session, item_id: uuid.UUID, kind: str | None = None, staff: bool = False) -> TryOnItem:
    item = db.get(TryOnItem, item_id)
    if item is None or (kind and item.kind != kind) or (not staff and (not item.is_active or item.content_status != "approved")):
        raise AppError(404, "not_found")
    return item


@catalogue.get("/items/{item_id}/image")
def tryon_image(item_id: uuid.UUID, db: Session = Depends(get_db), storage: Storage = Depends(get_storage)) -> Response:
    """The cut-out with a transparent background, for the picker."""
    item = _item(db, item_id)
    return Response(storage.get(item.asset_key), media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


class TryOnIn(BaseModel):
    image_id: uuid.UUID
    item_id: uuid.UUID
    colour: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


@previews_router.post("/garment", dependencies=[Depends(require_feature("phase1.virtual_tryon"))], response_class=Response)
def garment_preview(body: TryOnIn, user: User = Depends(get_current_user), db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    """A catalogue garment fitted onto the user's full-length photo."""
    item = _item(db, body.item_id, "garment")
    template = tryon.decode(storage.get(item.asset_key), item.anchors)
    return _render(db, storage, user, body.image_id, "full_body", lambda rgb: tryon.apply_garment(rgb, template))


@previews_router.post("/hairstyle", dependencies=[Depends(require_feature("phase1.hair_preview"))], response_class=Response)
def hairstyle_preview(body: TryOnIn, user: User = Depends(get_current_user), db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    """A catalogue hairstyle (cut and style) on the user's face photo, optionally in another colour."""
    item = _item(db, body.item_id, "hairstyle")
    template = tryon.decode(storage.get(item.asset_key), item.anchors)
    return _render(db, storage, user, body.image_id, "face", lambda rgb: tryon.apply_hairstyle(rgb, template, body.colour))


admin_tryon = APIRouter(prefix="/admin/tryon-items", tags=["admin: try-on library"])


def admin_tryon_out(item: TryOnItem) -> dict:
    return {"id": item.id, "kind": item.kind, "title": item.title, "category": item.category, "tags": item.tags,
            "licence": item.licence, "content_status": item.content_status, "is_active": item.is_active,
            "retail_item_id": item.retail_item_id, "created_at": item.created_at}


@admin_tryon.post("", status_code=status.HTTP_201_CREATED)
async def create_tryon_item(
    file: UploadFile = File(...), kind: str = Form(..., pattern="^(garment|hairstyle)$"),
    title_en: str = Form(..., min_length=1, max_length=120), title_ar: str = Form(..., min_length=1, max_length=120),
    licence: str = Form(..., min_length=3, max_length=300), category: str | None = Form(default=None, max_length=30),
    _: User = Depends(require_permission("content.manage")), db: Session = Depends(get_db), storage: Storage = Depends(get_storage),
) -> dict:
    """Cut the garment or hairstyle out of a reference photo. The item starts as a draft:
    check the cut-out (GET .../image) and approve it before customers see it."""
    data = await file.read(10 * 1024 * 1024 + 1)
    if (file.content_type or "") not in ("image/jpeg", "image/png"):
        raise AppError(415, "unsupported_image_type")
    if len(data) > 10 * 1024 * 1024:
        raise AppError(413, "image_too_large")
    try:
        rgb = engine.decode(data)
        template = tryon.extract_garment(rgb) if kind == "garment" else tryon.extract_hairstyle(rgb)
    except engine.ModelsMissing as exc:
        raise AppError(503, "analysis_unavailable") from exc
    except Unusable as exc:
        raise AppError(422, "photo_not_analysable", {"reasons": exc.reasons}) from exc
    except ValueError as exc:
        raise AppError(422, "photo_not_analysable", {"reasons": ["not_an_image"]}) from exc
    item_id = uuid.uuid4()
    extension = "png" if file.content_type == "image/png" else "jpg"
    item = TryOnItem(id=item_id, kind=kind, title={"en": title_en, "ar": title_ar}, category=category, licence=licence,
                     source_key=f"tryon/{item_id}/source.{extension}", asset_key=f"tryon/{item_id}/cutout.png",
                     anchors=template.anchors, tags={})
    storage.put(item.source_key, data)
    storage.put(item.asset_key, tryon.encode(template))
    db.add(item)
    db.flush()
    return admin_tryon_out(item)


@admin_tryon.get("")
def list_tryon_items(_: User = Depends(require_permission("content.manage")), db: Session = Depends(get_db)) -> list[dict]:
    return [admin_tryon_out(i) for i in db.scalars(select(TryOnItem).order_by(TryOnItem.created_at.desc()))]


@admin_tryon.get("/{item_id}/image")
def admin_tryon_image(item_id: uuid.UUID, _: User = Depends(require_permission("content.manage")),
                      db: Session = Depends(get_db), storage: Storage = Depends(get_storage)) -> Response:
    return Response(storage.get(_item(db, item_id, staff=True).asset_key), media_type="image/png", headers={"Cache-Control": "no-store"})


class TryOnPatch(BaseModel):
    title: dict[str, str] | None = None
    category: str | None = Field(default=None, max_length=30)
    tags: dict[str, list[str]] | None = None
    content_status: str | None = Field(default=None, pattern="^(draft|approved)$")
    is_active: bool | None = None
    retail_item_id: uuid.UUID | None = None


@admin_tryon.patch("/{item_id}")
def patch_tryon_item(item_id: uuid.UUID, body: TryOnPatch, _: User = Depends(require_permission("content.manage")), db: Session = Depends(get_db)) -> dict:
    item = _item(db, item_id, staff=True)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(item, key, value)
    db.flush()
    return admin_tryon_out(item)


@admin_tryon.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tryon_item(item_id: uuid.UUID, _: User = Depends(require_permission("content.manage")),
                      db: Session = Depends(get_db), storage: Storage = Depends(get_storage)) -> None:
    item = _item(db, item_id, staff=True)
    storage.delete(item.asset_key)
    storage.delete(item.source_key)
    db.delete(item)


# ---------------------------------------------------------------- twelve colour types and palettes

colour_types_router = APIRouter(prefix="/colour-types", tags=["colour types"], dependencies=[Depends(get_current_user)])


@colour_types_router.get("")
def colour_type_list(request: Request) -> list[dict]:
    """All twelve types, each with a few signature colours, for pickers and explainers."""
    language = pick_language(request)
    return [{"key": t.key, "season": t.season, "dominant": t.dominant, "title": t.title.get(language, t.title["en"]),
             "signature": colour_types.palette(t.key)["signature"]} for t in colour_types.TYPES]


@colour_types_router.get("/{key}")
def colour_type_detail(key: str, request: Request) -> dict:
    """One type's full palette: neutrals, colours, lips, hair, metals and colours to avoid."""
    if key not in colour_types.BY_KEY:
        raise AppError(404, "not_found")
    return colour_types.summary(key, pick_language(request))
