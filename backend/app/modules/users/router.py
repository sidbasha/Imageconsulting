import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.core.errors import AppError, pick_language
from app.database.session import get_db
from app.integrations.storage import Storage, get_storage
from app.integrations.uae_pass import InvalidCode, get_uae_pass
from app.modules.assessments.service import tr
from app.modules.auth.models import User
from app.modules.feature_flags.guard import enabled_features, require_feature
from app.modules.platform import service as platform
from app.modules.platform.models import PlatformSetting
from app.modules.users import service
from app.modules.users.models import CustomerProfile, IdentityVerification

router = APIRouter(tags=["profile"])


class ProfileIn(BaseModel):
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, pattern="^(female|male)$")
    country_code: str | None = Field(default=None, pattern="^[A-Za-z]{2}$")
    city: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9 ]{7,20}$")


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    date_of_birth: date | None
    gender: str | None
    country_code: str | None
    city: str | None
    phone: str | None
    eligibility_status: str
    eligibility_reasons: list[str]
    identity_status: str


@router.get("/users/me/profile", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db), on: set[str] = Depends(enabled_features)):
    return service.evaluate(db, service.profile_for(db, user), on)


@router.put("/users/me/profile", response_model=ProfileOut)
def put_profile(
    body: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db), on: set[str] = Depends(enabled_features)
):
    return service.update_profile(db, user, on, **body.model_dump())


@router.get("/countries")
def countries(request: Request, db: Session = Depends(get_db), on: set[str] = Depends(enabled_features)) -> list[dict]:
    """Markets a user may choose: UAE at launch, more once international expansion is released."""
    language = pick_language(request)
    return [
        {"code": c.code, "name": tr(c.name, language), "currency": c.currency}
        for c in platform.available_countries(db, on)
    ]


# ---------------------------------------------------------------- identity (row 1)

identity = APIRouter(prefix="/identity", tags=["identity"], dependencies=[Depends(require_feature("phase1.identity_verification"))])


class VerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    method: str
    status: str
    reason: str | None
    created_at: datetime
    reviewed_at: datetime | None


@identity.get("/uae-pass/start")
def uae_pass_start(user: User = Depends(get_current_user)) -> dict:
    provider = _provider()
    return {"provider": provider.name, "authorize_url": provider.authorize_url(state=str(user.id))}


class CodeIn(BaseModel):
    code: str = Field(min_length=10, max_length=4000)


@identity.post("/uae-pass/complete", response_model=VerificationOut, status_code=status.HTTP_201_CREATED)
def uae_pass_complete(
    body: CodeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db), on: set[str] = Depends(enabled_features)
):
    try:
        result = _provider().exchange(body.code)
    except InvalidCode as exc:
        raise AppError(422, "invalid_verification_code") from exc
    return service.verify_with_uae_pass(db, user, result, on)


def _provider():
    try:
        return get_uae_pass()
    except RuntimeError as exc:
        raise AppError(503, "integration_not_configured", {"integration": "uae_pass"}) from exc


@identity.post("/documents", response_model=VerificationOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    front: UploadFile = File(...),
    back: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    files = []
    for upload in (front, back):
        if upload is not None:
            files.append((await upload.read(service.MAX_ID_BYTES + 1), upload.content_type or ""))
    return service.submit_document(db, storage, user, files)


@identity.get("/verifications", response_model=list[VerificationOut])
def my_verifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(IdentityVerification)
            .where(IdentityVerification.user_id == user.id)
            .order_by(IdentityVerification.created_at.desc())
        )
    )


# ---------------------------------------------------------------- admin (row 53, settings)

admin = APIRouter(prefix="/admin", tags=["admin: users"])


@admin.get("/identity/pending")
def pending_documents(
    _: User = Depends(require_permission("users.review")), db: Session = Depends(get_db)
) -> list[dict]:
    rows = db.execute(
        select(IdentityVerification, User)
        .join(User, User.id == IdentityVerification.user_id)
        .where(IdentityVerification.status == "pending")
        .order_by(IdentityVerification.created_at)
    ).all()
    return [
        {"id": v.id, "user_id": u.id, "full_name": u.full_name, "email": u.email,
         "documents": len(v.document_keys), "created_at": v.created_at}
        for v, u in rows
    ]


@admin.get("/identity/{verification_id}/documents/{index}")
def document_file(
    verification_id: uuid.UUID, index: int,
    _: User = Depends(require_permission("users.review")),
    db: Session = Depends(get_db), storage: Storage = Depends(get_storage),
):
    from fastapi import Response

    record = db.get(IdentityVerification, verification_id)
    if record is None or not 0 <= index < len(record.document_keys):
        raise AppError(404, "not_found")
    key = record.document_keys[index]
    media = {"jpg": "image/jpeg", "png": "image/png", "pdf": "application/pdf"}[key.rsplit(".", 1)[1]]
    return Response(storage.get(key), media_type=media, headers={"Cache-Control": "no-store"})


class DocumentReviewIn(BaseModel):
    approve: bool
    reason: str | None = Field(default=None, max_length=300)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, pattern="^(female|male)$")


@admin.post("/identity/{verification_id}/review", response_model=VerificationOut)
def review_document(
    verification_id: uuid.UUID, body: DocumentReviewIn,
    reviewer: User = Depends(require_permission("users.review")),
    db: Session = Depends(get_db), storage: Storage = Depends(get_storage), on: set[str] = Depends(enabled_features),
):
    if body.approve and (body.date_of_birth is None or body.gender is None):
        raise AppError(422, "invalid_profile", {"field": "date_of_birth and gender are read off the document"})
    return service.review_document(
        db, storage, reviewer, verification_id, approve=body.approve, reason=body.reason,
        date_of_birth=body.date_of_birth, gender=body.gender, enabled=on,
    )


@admin.get("/eligibility")
def eligibility_queue(
    status_filter: str = "pending_review",
    _: User = Depends(require_permission("users.review")), db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.execute(
        select(CustomerProfile, User).join(User, User.id == CustomerProfile.user_id)
        .where(CustomerProfile.eligibility_status == status_filter).order_by(CustomerProfile.updated_at)
    ).all()
    return [
        {"user_id": u.id, "full_name": u.full_name, "email": u.email, "status": p.eligibility_status,
         "reasons": p.eligibility_reasons, "identity_status": p.identity_status}
        for p, u in rows
    ]


class EligibilityReviewIn(BaseModel):
    approve: bool


@admin.post("/eligibility/{user_id}", response_model=ProfileOut)
def review_eligibility(
    user_id: uuid.UUID, body: EligibilityReviewIn,
    reviewer: User = Depends(require_permission("users.review")),
    db: Session = Depends(get_db), on: set[str] = Depends(enabled_features),
):
    return service.review_eligibility(db, reviewer, user_id, body.approve, on)


@admin.get("/settings")
def list_settings(_: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)) -> list[dict]:
    stored = {s.key: s for s in db.scalars(select(PlatformSetting))}
    return [
        {"key": key, "value": stored[key].value if key in stored else default, "description": description}
        for key, (default, description) in platform.DEFAULTS.items()
    ]


class SettingIn(BaseModel):
    value: bool | int | float | str | dict | list


@admin.put("/settings/{key}")
def put_setting(
    key: str, body: SettingIn, _: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)
) -> dict:
    row = platform.set_value(db, key, body.value)
    return {"key": row.key, "value": row.value}


class CountryIn(BaseModel):
    is_enabled: bool


@admin.put("/countries/{code}")
def put_country(
    code: str, body: CountryIn, _: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)
) -> dict:
    from app.modules.platform.models import Country

    country = db.execute(select(Country).where(Country.code == code.upper())).scalar_one_or_none()
    if country is None:
        raise AppError(404, "not_found")
    if country.is_launch_market and not body.is_enabled:
        raise AppError(409, "launch_market_required")
    country.is_enabled = body.is_enabled
    db.flush()
    return {"code": country.code, "is_enabled": country.is_enabled}
