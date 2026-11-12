import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.core.errors import AppError
from app.database.session import get_db
from app.integrations.payments import PaymentProvider
from app.integrations.storage import Storage, get_storage
from app.modules.auth.models import User
from app.modules.commerce.router import payments_provider
from app.modules.feature_flags.guard import enabled_features, require_feature
from app.modules.marketplace import service
from app.modules.marketplace.models import (
    AvailabilitySlot,
    Booking,
    Credential,
    StylistProfile,
    StylistService,
    Testimonial,
)
from app.modules.users.deps import eligible_user, verified_user


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    display_name: str
    bio: str
    city: str | None
    latitude: float | None
    longitude: float | None
    languages: list[str]
    specialities: list[str]
    years_experience: int | None
    business_license_no: str | None
    status: str
    review_note: str | None
    rating_avg: float
    rating_count: int


class ApplicationIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=4000)
    city: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    languages: list[str] | None = None
    specialities: list[str] | None = None
    years_experience: int | None = Field(default=None, ge=0, le=80)
    business_license_no: str | None = Field(default=None, max_length=60)


class CredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    title: str
    status: str
    note: str | None
    created_at: datetime


# ---------------------------------------------------------------- stylist application (15, 16)

application = APIRouter(prefix="/stylist/application", tags=["stylist application"],
                        dependencies=[Depends(require_feature("phase2.stylist_onboarding"))])


@application.get("", response_model=ProfileOut | None)
def get_application(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.my_profile(db, user)


@application.put("", response_model=ProfileOut)
def put_application(body: ApplicationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.save_application(db, user, body.model_dump())


@application.post("/credentials", response_model=CredentialOut, status_code=status.HTTP_201_CREATED,
                  dependencies=[Depends(require_feature("phase2.credential_submission"))])
async def upload_credential(
    kind: str = Form(...), title: str = Form(..., min_length=1, max_length=160), file: UploadFile = File(...),
    user: User = Depends(get_current_user), db: Session = Depends(get_db), storage: Storage = Depends(get_storage),
):
    data = await file.read(service.MAX_CREDENTIAL_BYTES + 1)
    return service.add_credential(db, storage, user, kind=kind, title=title, data=data, content_type=file.content_type or "")


@application.get("/credentials", response_model=list[CredentialOut])
def my_credentials(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = service.require_profile(db, user)
    return list(db.scalars(select(Credential).where(Credential.profile_id == profile.id).order_by(Credential.created_at)))


@application.post("/submit", response_model=ProfileOut)
def submit(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.submit_application(db, user)


# ---------------------------------------------------------------- stylist practice: services, slots, bookings

practice = APIRouter(prefix="/stylist", tags=["stylist practice"], dependencies=[Depends(require_feature("phase2.stylist_discovery"))])


class ServiceIn(BaseModel):
    kind: str = Field(pattern="^(consultation|occasion_audit|wardrobe_audit|makeup_audit|expert_color|personal_shopper_day)$")
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    price_minor: int = Field(ge=0, le=10_000_000)
    duration_minutes: int = Field(default=30, ge=15, le=600)
    mode: str = Field(default="online", pattern="^(online|in_person)$")
    is_active: bool = True


@practice.get("/services")
def my_services(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    profile = service.require_profile(db, user)
    return [service.service_out(s) | {"is_active": s.is_active}
            for s in db.scalars(select(StylistService).where(StylistService.profile_id == profile.id))]


@practice.post("/services", status_code=status.HTTP_201_CREATED)
def add_service(body: ServiceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db), on: set[str] = Depends(enabled_features)) -> dict:
    profile = service.require_practising(db, user, on)
    if service.SERVICE_FEATURES[body.kind] not in on:
        raise AppError(404, "feature_not_available")
    if body.kind in service.IN_PERSON_ONLY and body.mode != "in_person":
        raise AppError(422, "in_person_only")
    item = StylistService(profile_id=profile.id, **body.model_dump())
    db.add(item)
    db.flush()
    return service.service_out(item)


@practice.put("/services/{service_id}")
def put_service(service_id: uuid.UUID, body: ServiceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db),
                on: set[str] = Depends(enabled_features)) -> dict:
    profile = service.require_practising(db, user, on)
    item = db.get(StylistService, service_id)
    if item is None or item.profile_id != profile.id:
        raise AppError(404, "not_found")
    for k, v in body.model_dump().items():
        setattr(item, k, v)
    db.flush()
    return service.service_out(item)


class SlotsIn(BaseModel):
    starts: list[datetime] = Field(min_length=1, max_length=200)
    minutes: int = Field(default=30, ge=15, le=600)


@practice.post("/slots", status_code=status.HTTP_201_CREATED)
def add_slots(body: SlotsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db), on: set[str] = Depends(enabled_features)) -> list[dict]:
    profile = service.require_practising(db, user, on)
    return [{"id": s.id, "starts_at": s.starts_at, "ends_at": s.ends_at} for s in service.add_slots(db, profile, body.starts, body.minutes)]


@practice.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_slot(slot_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    profile = service.require_profile(db, user)
    slot = db.get(AvailabilitySlot, slot_id)
    if slot is None or slot.profile_id != profile.id:
        raise AppError(404, "not_found")
    if slot.booking_id is not None:
        raise AppError(409, "slot_booked")
    db.delete(slot)


@practice.get("/bookings")
def stylist_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    profile = service.require_profile(db, user)
    return [service.booking_out(b) for b in db.scalars(
        select(Booking).where(Booking.profile_id == profile.id, Booking.status.in_(("confirmed", "completed", "cancelled")))
        .order_by(Booking.starts_at))]


@practice.post("/bookings/{booking_id}/complete")
def complete(booking_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return service.booking_out(service.complete(db, user, booking_id))


# ---------------------------------------------------------------- discovery (18, 47)

discovery = APIRouter(prefix="/stylists", tags=["stylists"], dependencies=[Depends(require_feature("phase2.stylist_discovery"))])


@discovery.get("")
def find(
    kind: str | None = None, city: str | None = None, language: str | None = None,
    lat: float | None = None, lng: float | None = None, radius_km: float | None = Query(default=None, gt=0),
    on: set[str] = Depends(enabled_features), _: User = Depends(eligible_user), db: Session = Depends(get_db),
) -> list[dict]:
    return service.discover(db, on, kind=kind, city=city, language=language, lat=lat, lng=lng, radius_km=radius_km)


@discovery.get("/{profile_id}")
def stylist(profile_id: uuid.UUID, on: set[str] = Depends(enabled_features), _: User = Depends(eligible_user), db: Session = Depends(get_db)) -> dict:
    profile = db.get(StylistProfile, profile_id)
    if profile is None or profile.status != "approved":
        raise AppError(404, "not_found")
    services = [service.service_out(s) for s in db.scalars(select(StylistService).where(
        StylistService.profile_id == profile.id, StylistService.is_active)) if service.SERVICE_FEATURES.get(s.kind) in on]
    testimonials = []
    if "phase2.testimonials" in on:
        testimonials = [{"rating": t.rating, "text": t.text, "created_at": t.created_at} for t in db.scalars(
            select(Testimonial).where(Testimonial.profile_id == profile.id, Testimonial.status == "published")
            .order_by(Testimonial.created_at.desc()).limit(20))]
    return {"id": profile.id, "display_name": profile.display_name, "bio": profile.bio, "city": profile.city,
            "languages": profile.languages, "specialities": profile.specialities, "years_experience": profile.years_experience,
            "rating_avg": round(profile.rating_avg, 2), "rating_count": profile.rating_count,
            "services": services, "testimonials": testimonials,
            "slots": [{"id": s.id, "starts_at": s.starts_at, "ends_at": s.ends_at} for s in service.open_slots(db, profile.id)]}


# ---------------------------------------------------------------- bookings (19, 41, 44, 46)

bookings = APIRouter(prefix="/bookings", tags=["bookings"], dependencies=[Depends(require_feature("phase2.booking"))])


class AddressIn(BaseModel):
    line1: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=80)
    notes: str | None = Field(default=None, max_length=300)


class BookIn(BaseModel):
    service_id: uuid.UUID
    slot_id: uuid.UUID
    use_reward: bool = False
    address: AddressIn | None = None


@bookings.post("", status_code=status.HTTP_201_CREATED)
def book(body: BookIn, on: set[str] = Depends(enabled_features), user: User = Depends(verified_user),
         db: Session = Depends(get_db), payments: PaymentProvider = Depends(payments_provider)) -> dict:
    return service.book(db, payments, user, on, service_id=body.service_id, slot_id=body.slot_id,
                        use_reward=body.use_reward, address=body.address.model_dump() if body.address else None)


@bookings.get("")
def my_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    service.release_lapsed_holds(db)
    return [service.booking_out(b) for b in db.scalars(
        select(Booking).where(Booking.customer_id == user.id).order_by(Booking.starts_at.desc()))]


@bookings.get("/{booking_id}")
def one_booking(booking_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    booking = db.get(Booking, booking_id)
    if booking is None or user.id not in (booking.customer_id, booking.profile.user_id):
        raise AppError(404, "not_found")
    return service.booking_out(booking)


@bookings.post("/{booking_id}/cancel")
def cancel(booking_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db),
           payments: PaymentProvider = Depends(payments_provider)) -> dict:
    return service.booking_out(service.cancel(db, payments, user, booking_id))


class TestimonialIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=2000)


@bookings.post("/{booking_id}/testimonial", status_code=status.HTTP_201_CREATED,
               dependencies=[Depends(require_feature("phase2.testimonials"))])
def testimonial(booking_id: uuid.UUID, body: TestimonialIn, user: User = Depends(eligible_user), db: Session = Depends(get_db)) -> dict:
    t = service.add_testimonial(db, user, booking_id, body.rating, body.text)
    return {"id": t.id, "rating": t.rating, "status": t.status}


# ---------------------------------------------------------------- admin (53, 54)

admin = APIRouter(prefix="/admin/stylists", tags=["admin: stylists"])


@admin.get("")
def applications(status_filter: str = "submitted", _: User = Depends(require_permission("stylists.review")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(StylistProfile).where(StylistProfile.status == status_filter).order_by(StylistProfile.updated_at))
    out = []
    for p in rows:
        creds = db.scalars(select(Credential).where(Credential.profile_id == p.id)).all()
        out.append(ProfileOut.model_validate(p).model_dump() | {
            "credentials": [CredentialOut.model_validate(c).model_dump() for c in creds]})
    return out


@admin.get("/credentials/{credential_id}/file")
def credential_file(credential_id: uuid.UUID, _: User = Depends(require_permission("stylists.review")),
                    db: Session = Depends(get_db), storage: Storage = Depends(get_storage)) -> Response:
    credential = db.get(Credential, credential_id)
    if credential is None:
        raise AppError(404, "not_found")
    return Response(storage.get(credential.storage_key), media_type=credential.content_type, headers={"Cache-Control": "no-store"})


class DecisionIn(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=500)


@admin.post("/credentials/{credential_id}/review", response_model=CredentialOut)
def review_credential(credential_id: uuid.UUID, body: DecisionIn, reviewer: User = Depends(require_permission("stylists.review")), db: Session = Depends(get_db)):
    return service.review_credential(db, reviewer, credential_id, body.approve, body.note)


@admin.post("/{profile_id}/decision", response_model=ProfileOut,
            dependencies=[Depends(require_feature("phase2.stylist_verification"))])
def decide(profile_id: uuid.UUID, body: DecisionIn, reviewer: User = Depends(require_permission("stylists.review")), db: Session = Depends(get_db)):
    return service.decide_application(db, reviewer, profile_id, body.approve, body.note)


class TestimonialPatch(BaseModel):
    status: str = Field(pattern="^(published|hidden)$")


@admin.patch("/testimonials/{testimonial_id}")
def moderate_testimonial(testimonial_id: uuid.UUID, body: TestimonialPatch, _: User = Depends(require_permission("moderation.manage")),
                         db: Session = Depends(get_db)) -> dict:
    t = db.get(Testimonial, testimonial_id)
    if t is None:
        raise AppError(404, "not_found")
    t.status = body.status
    db.flush()
    service.recompute_rating(db, t.profile_id)
    return {"id": t.id, "status": t.status}

