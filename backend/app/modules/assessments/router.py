import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.errors import AppError, pick_language
from app.database.session import get_db
from app.integrations.storage import Storage, get_storage
from app.modules.assessments import service
from app.modules.assessments.models import AssessmentImage, Questionnaire
from app.modules.auth.models import User
from app.modules.feature_flags.guard import enabled_features, require_feature
from app.modules.users.deps import eligible_user

# Customer features: closed to customers who do not meet the eligibility rules.
router = APIRouter(dependencies=[Depends(eligible_user)])


class AnswersIn(BaseModel):
    answers: dict[str, str] = Field(description="{question key: chosen option key}")


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    width: int
    height: int
    size_bytes: int
    quality: dict
    consent_at: datetime
    created_at: datetime


enabled = enabled_features


@router.get("/assessments", tags=["assessments"])
def list_assessments(
    request: Request, on: set[str] = Depends(enabled), user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    """Questionnaires available in the current release, with the user's latest result."""
    language = pick_language(request)
    items = []
    for q in db.scalars(select(Questionnaire).where(Questionnaire.is_active).order_by(Questionnaire.sort_order)):
        if q.feature_key not in on:
            continue
        done = service.latest(db, user, q)
        profile = done and next((p for p in q.profiles if p.key == done.profile_key), None)
        items.append(
            {
                "key": q.key,
                "title": service.tr(q.title, language),
                "completed_at": done and done.created_at,
                "result": profile and service.tr(profile.title, language),
            }
        )
    return items


@router.get("/assessments/{key}", tags=["assessments"])
def get_questionnaire(
    key: str, request: Request, on: set[str] = Depends(enabled), _: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    return service.describe_questionnaire(service.get_questionnaire(db, key, on), pick_language(request))


@router.post("/assessments/{key}/responses", status_code=status.HTTP_201_CREATED, tags=["assessments"])
def submit(
    key: str,
    body: AnswersIn,
    request: Request,
    on: set[str] = Depends(enabled),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    questionnaire = service.get_questionnaire(db, key, on)
    assessment = service.submit(db, user, questionnaire, body.answers)
    return service.describe_result(questionnaire, assessment, pick_language(request))


@router.get("/assessments/{key}/result", tags=["assessments"])
def latest_result(
    key: str, request: Request, on: set[str] = Depends(enabled), user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict | None:
    """The user's most recent result, or null if they have not completed it."""
    questionnaire = service.get_questionnaire(db, key, on)
    assessment = service.latest(db, user, questionnaire)
    return assessment and service.describe_result(questionnaire, assessment, pick_language(request))


@router.get("/recommendations/{category}", tags=["recommendations"])
def recommendations(
    category: str, request: Request, on: set[str] = Depends(enabled), user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Advice for outfits, eyewear or hair, drawn from the user's own results."""
    return service.recommendations(db, user, category, on, pick_language(request))


images = APIRouter(
    prefix="/assessment-images",
    tags=["assessment-images"],
    dependencies=[Depends(require_feature("phase1.photo_assessment")), Depends(eligible_user)],
)


@images.post("", response_model=ImageOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    kind: str = Form(...),
    consent: bool = Form(..., description="The user agreed to their photo being processed"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> AssessmentImage:
    # Read one byte past the limit so an oversized upload is rejected without buffering it all.
    data = await file.read(service.MAX_UPLOAD_BYTES + 1)
    return service.store_image(
        db, storage, user, data=data, content_type=file.content_type or "", kind=kind, consent=consent
    )


@images.get("", response_model=list[ImageOut])
def list_images(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[AssessmentImage]:
    return service.list_images(db, user)


@images.get("/{image_id}/file", response_class=Response)
def image_file(
    image_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> Response:
    """The user's own photo, for thumbnails. Never cached by shared caches."""
    image = service.own_image(db, user, image_id)
    try:
        data = storage.get(image.storage_key)
    except FileNotFoundError:
        raise AppError(404, "not_found") from None
    return Response(data, media_type=image.content_type, headers={"Cache-Control": "private, no-store"})


@images.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    image_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> None:
    service.delete_image(db, storage, user, image_id)
