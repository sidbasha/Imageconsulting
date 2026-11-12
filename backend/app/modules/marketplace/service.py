"""Stylists, discovery, booking and testimonials (rows 15-19, 45-47).

Ranking (row 66) is undecided; the weights are a setting. Booking a slot
holds it while the customer pays; unpaid holds lapse after HOLD_MINUTES.
"""

import math
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.integrations.payments import PaymentProvider
from app.integrations.storage import Storage
from app.modules.auth.models import Role, User
from app.modules.commerce import service as commerce
from app.modules.commerce.models import Order
from app.modules.marketplace.models import (
    AvailabilitySlot,
    Booking,
    Credential,
    StylistProfile,
    StylistService,
    Testimonial,
)
from app.modules.platform import service as platform

HOLD_MINUTES = 15
CREDENTIAL_KINDS = ("certification", "practice_evidence", "invoice", "testimonial", "referral", "business_license")
CREDENTIAL_TYPES = {"image/jpeg": "jpg", "image/png": "png", "application/pdf": "pdf"}
MAX_CREDENTIAL_BYTES = 10 * 1024 * 1024

# Service kind -> the release switch that must be on to offer or book it.
SERVICE_FEATURES = {
    "consultation": "phase2.consultations",
    "occasion_audit": "phase2.occasion_audit",
    "wardrobe_audit": "phase2.wardrobe_audit",
    "makeup_audit": "phase2.makeup_audit",
    "expert_color": "phase2.expert_color_analysis",
    "personal_shopper_day": "phase3.personal_shopper",
}
IN_PERSON_ONLY = {"personal_shopper_day"}


def now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------- applications (15-17)

def my_profile(db: Session, user: User) -> StylistProfile | None:
    return db.execute(select(StylistProfile).where(StylistProfile.user_id == user.id)).scalar_one_or_none()


def require_profile(db: Session, user: User) -> StylistProfile:
    profile = my_profile(db, user)
    if profile is None:
        raise AppError(404, "not_found")
    return profile


def save_application(db: Session, user: User, fields: dict) -> StylistProfile:
    profile = my_profile(db, user)
    if profile is None:
        profile = StylistProfile(user_id=user.id, display_name=fields.get("display_name") or user.full_name)
        db.add(profile)
    elif profile.status in ("submitted",):
        raise AppError(409, "application_under_review")
    for key, value in fields.items():
        if value is not None:
            setattr(profile, key, value)
    if profile.status == "rejected":
        profile.status = "draft"  # editing a rejected application starts it again
    db.flush()
    return profile


def add_credential(db: Session, storage: Storage, user: User, *, kind: str, title: str, data: bytes, content_type: str) -> Credential:
    profile = require_profile(db, user)
    if profile.status == "submitted":
        raise AppError(409, "application_under_review")
    if kind not in CREDENTIAL_KINDS:
        raise AppError(422, "invalid_credential_kind")
    if content_type not in CREDENTIAL_TYPES:
        raise AppError(415, "unsupported_document_type")
    if len(data) > MAX_CREDENTIAL_BYTES:
        raise AppError(413, "document_too_large")
    credential = Credential(id=uuid.uuid4(), profile_id=profile.id, kind=kind, title=title, content_type=content_type)
    credential.storage_key = f"credentials/{profile.id}/{credential.id}.{CREDENTIAL_TYPES[content_type]}"
    storage.put(credential.storage_key, data)
    db.add(credential)
    db.flush()
    return credential


def submit_application(db: Session, user: User) -> StylistProfile:
    profile = require_profile(db, user)
    if profile.status not in ("draft", "rejected"):
        raise AppError(409, "application_not_editable")
    if not profile.bio or not profile.city:
        raise AppError(422, "application_incomplete", {"missing": [f for f in ("bio", "city") if not getattr(profile, f)]})
    if not db.scalar(select(func.count()).select_from(Credential).where(Credential.profile_id == profile.id)):
        raise AppError(422, "application_incomplete", {"missing": ["credentials"]})
    profile.status = "submitted"
    db.flush()
    return profile


def review_credential(db: Session, reviewer: User, credential_id: uuid.UUID, accept: bool, note: str | None) -> Credential:
    credential = db.get(Credential, credential_id)
    if credential is None:
        raise AppError(404, "not_found")
    credential.status = "accepted" if accept else "rejected"
    credential.note, credential.reviewed_by, credential.reviewed_at = note, reviewer.id, now()
    db.flush()
    return credential


def decide_application(db: Session, reviewer: User, profile_id: uuid.UUID, approve: bool, note: str | None) -> StylistProfile:
    profile = db.get(StylistProfile, profile_id)
    if profile is None:
        raise AppError(404, "not_found")
    if profile.status not in ("submitted", "suspended", "approved"):
        raise AppError(409, "application_not_submitted")
    if approve:
        accepted = db.scalar(select(func.count()).select_from(Credential).where(
            Credential.profile_id == profile.id, Credential.status == "accepted"))
        if not accepted:
            raise AppError(409, "no_accepted_credentials")  # manual vetting first (row 17)
    profile.status = "approved" if approve else ("rejected" if profile.status == "submitted" else "suspended")
    profile.review_note, profile.reviewed_by, profile.reviewed_at = note, reviewer.id, now()
    user = db.get(User, profile.user_id)
    if approve and user.role.key == "customer":
        user.role = db.execute(select(Role).where(Role.key == "stylist")).scalar_one()
    db.flush()
    return profile


# ---------------------------------------------------------------- services and availability

def require_practising(db: Session, user: User, enabled: set[str]) -> StylistProfile:
    profile = require_profile(db, user)
    if profile.status != "approved":
        raise AppError(403, "stylist_not_approved")
    if "phase2.consultant_subscriptions" in enabled and not commerce.has_entitlement(db, user, "consultant.membership"):
        raise AppError(402, "membership_required")  # row 40: annual participation fee
    return profile


def add_slots(db: Session, profile: StylistProfile, starts: list[datetime], minutes: int) -> list[AvailabilitySlot]:
    existing = set(db.scalars(select(AvailabilitySlot.starts_at).where(AvailabilitySlot.profile_id == profile.id)))
    slots = []
    for start in starts:
        if start.tzinfo is None:
            raise AppError(422, "timezone_required")
        if start <= now():
            raise AppError(422, "slot_in_past")
        if start in existing:
            continue
        slot = AvailabilitySlot(profile_id=profile.id, starts_at=start, ends_at=start + timedelta(minutes=minutes))
        db.add(slot)
        slots.append(slot)
    db.flush()
    return slots


def release_lapsed_holds(db: Session) -> int:
    lapsed = db.scalars(select(Booking).where(Booking.status == "pending_payment", Booking.hold_expires_at < now()))
    count = 0
    for booking in lapsed:
        booking.status, booking.cancelled_by = "expired", "system"
        _free_slot(db, booking)
        count += 1
    db.flush()
    return count


def _free_slot(db: Session, booking: Booking) -> None:
    if booking.slot_id:
        slot = db.get(AvailabilitySlot, booking.slot_id)
        if slot and slot.booking_id == booking.id:
            slot.booking_id = None


# ---------------------------------------------------------------- discovery (18, 47, 66)

def _distance_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def discover(db: Session, enabled: set[str], *, kind: str | None, city: str | None, language: str | None,
             lat: float | None, lng: float | None, radius_km: float | None) -> list[dict]:
    from app.modules.promotions.service import promoted_profile_ids  # late: promotions builds on marketplace

    weights = platform.get(db, "ranking.weights")
    promoted = promoted_profile_ids(db, enabled) if "phase2.paid_promotion" in enabled else set()
    use_location = "phase3.location_discovery" in enabled and lat is not None and lng is not None
    membership = "phase2.consultant_subscriptions" in enabled
    rows = []
    for profile in db.scalars(select(StylistProfile).where(StylistProfile.status == "approved")):
        if city and (profile.city or "").lower() != city.lower():
            continue
        if language and language not in profile.languages:
            continue
        if membership:
            owner = db.get(User, profile.user_id)
            if not commerce.has_entitlement(db, owner, "consultant.membership"):
                continue
        services = [s for s in db.scalars(select(StylistService).where(StylistService.profile_id == profile.id, StylistService.is_active))
                    if SERVICE_FEATURES.get(s.kind) in enabled]
        if kind:
            services = [s for s in services if s.kind == kind]
        if not services:
            continue
        distance = None
        if use_location and profile.latitude is not None:
            distance = _distance_km(lat, lng, profile.latitude, profile.longitude)
            if radius_km is not None and distance > radius_km:
                continue
        elif use_location and radius_km is not None:
            continue
        score = (weights.get("rating", 0) * profile.rating_avg
                 + weights.get("testimonials", 0) * math.log1p(profile.rating_count)
                 + weights.get("promoted", 0) * (profile.id in promoted)
                 - weights.get("distance", 0) * (math.log1p(distance) if distance is not None else 0))
        rows.append((score, profile, services, distance))
    rows.sort(key=lambda r: (-r[0], r[1].display_name))
    return [
        {"id": p.id, "display_name": p.display_name, "bio": p.bio, "city": p.city, "languages": p.languages,
         "specialities": p.specialities, "rating_avg": round(p.rating_avg, 2), "rating_count": p.rating_count,
         "promoted": p.id in promoted, "distance_km": None if d is None else round(d, 1),
         "services": [service_out(s) for s in services]}
        for _, p, services, d in rows
    ]


def service_out(s: StylistService) -> dict:
    return {"id": s.id, "kind": s.kind, "title": s.title, "description": s.description, "price_minor": s.price_minor,
            "currency": s.currency, "duration_minutes": s.duration_minutes, "mode": s.mode}


def open_slots(db: Session, profile_id: uuid.UUID) -> list[AvailabilitySlot]:
    release_lapsed_holds(db)
    return list(db.scalars(select(AvailabilitySlot).where(
        AvailabilitySlot.profile_id == profile_id, AvailabilitySlot.booking_id.is_(None),
        AvailabilitySlot.starts_at > now()).order_by(AvailabilitySlot.starts_at)))


# ---------------------------------------------------------------- booking (19, 41, 44, 46)

def book(db: Session, payments: PaymentProvider, customer: User, enabled: set[str], *, service_id: uuid.UUID,
         slot_id: uuid.UUID, use_reward: bool, address: dict | None) -> dict:
    release_lapsed_holds(db)
    service = db.get(StylistService, service_id)
    if service is None or not service.is_active or service.profile.status != "approved":
        raise AppError(404, "not_found")
    if SERVICE_FEATURES.get(service.kind) not in enabled:
        raise AppError(404, "feature_not_available")
    if service.profile.user_id == customer.id:
        raise AppError(409, "cannot_book_yourself")
    slot = db.execute(select(AvailabilitySlot).where(AvailabilitySlot.id == slot_id).with_for_update()).scalar_one_or_none()
    if slot is None or slot.profile_id != service.profile_id:
        raise AppError(404, "not_found")
    if slot.booking_id is not None or slot.starts_at <= now():
        raise AppError(409, "slot_unavailable")
    if service.mode == "in_person" and not address:
        raise AppError(422, "address_required")

    booking = Booking(
        id=uuid.uuid4(), customer_id=customer.id, profile_id=service.profile_id, service_id=service.id, slot_id=slot.id,
        kind=service.kind, starts_at=slot.starts_at, ends_at=slot.starts_at + timedelta(minutes=service.duration_minutes),
        price_minor=service.price_minor, currency=service.currency, hold_expires_at=now() + timedelta(minutes=HOLD_MINUTES),
        address=address if service.mode == "in_person" else None,
    )
    db.add(booking)
    slot.booking_id = booking.id
    db.flush()

    if use_reward:
        if "phase2.reward_redemption" not in enabled or service.kind != "consultation":
            raise AppError(422, "reward_not_applicable")
        commerce.consume_credit(db, customer, "reward.consultation")
        booking.paid_with = "reward"
        _confirm(db, booking)
        return {"booking": booking_out(booking), "checkout": None}
    if "phase2.service_payments" not in enabled:
        raise AppError(404, "feature_not_available")
    checkout = commerce.create_order(
        db, payments, customer, kind="booking", amount_minor=service.price_minor, currency=service.currency,
        items=[{"key": f"service.{service.kind}", "title": service.title, "quantity": 1, "unit_minor": service.price_minor}],
        description=service.title, target_id=booking.id,
    )
    booking.order_id = checkout["order_id"]
    db.flush()
    return {"booking": booking_out(booking), "checkout": checkout}


def _confirm(db: Session, booking: Booking) -> None:
    booking.status, booking.hold_expires_at = "confirmed", None
    from app.modules.consultations.service import open_for_booking  # late: consultations build on bookings

    open_for_booking(db, booking)
    db.flush()


def _on_booking_paid(db: Session, order: Order) -> None:
    booking = db.get(Booking, order.target_id)
    if booking.status == "pending_payment":
        booking.paid_with = "payment"
        _confirm(db, booking)
    elif booking.status in ("expired", "cancelled"):
        # Paid after the hold lapsed: give the money back rather than double-book.
        order.status = "refund_due"


def _on_booking_refunded(db: Session, order: Order) -> None:
    booking = db.get(Booking, order.target_id)
    if booking.status in ("pending_payment", "confirmed"):
        booking.status, booking.cancelled_by = "cancelled", booking.cancelled_by or "system"
        _free_slot(db, booking)


commerce.ON_PAID["booking"] = _on_booking_paid
commerce.ON_REFUNDED["booking"] = _on_booking_refunded


def cancel(db: Session, payments: PaymentProvider, user: User, booking_id: uuid.UUID) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise AppError(404, "not_found")
    is_customer = booking.customer_id == user.id
    is_stylist = booking.profile.user_id == user.id
    if not (is_customer or is_stylist):
        raise AppError(404, "not_found")
    if booking.status not in ("pending_payment", "confirmed"):
        raise AppError(409, "booking_not_cancellable")
    if is_customer and booking.status == "confirmed":
        cutoff = booking.starts_at - timedelta(hours=platform.get(db, "booking.cancel_hours"))
        if now() > cutoff:
            raise AppError(409, "too_late_to_cancel")
    booking.cancelled_by = "customer" if is_customer else "stylist"
    order = booking.order_id and db.get(Order, booking.order_id)
    if order and order.status == "paid":
        commerce.refund(db, payments, order)  # runs _on_booking_refunded
    else:
        if booking.paid_with == "reward":
            commerce.grant(db, booking.customer_id, "reward.consultation", "reward", booking.id)  # give the credit back
        booking.status = "cancelled"
        _free_slot(db, booking)
    db.flush()
    return booking


def complete(db: Session, user: User, booking_id: uuid.UUID) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.profile.user_id != user.id:
        raise AppError(404, "not_found")
    if booking.status != "confirmed":
        raise AppError(409, "booking_not_confirmed")
    booking.status = "completed"
    from app.modules.rewards.service import award

    award(db, booking.customer_id, "consultation_completed", ref=str(booking.id))
    db.flush()
    return booking


def booking_out(b: Booking) -> dict:
    return {"id": b.id, "status": b.status, "kind": b.kind, "starts_at": b.starts_at, "ends_at": b.ends_at,
            "price_minor": b.price_minor, "currency": b.currency, "paid_with": b.paid_with,
            "stylist": {"id": b.profile_id, "display_name": b.profile.display_name},
            "service": service_out(b.service), "customer_id": b.customer_id, "address": b.address,
            "hold_expires_at": b.hold_expires_at, "cancelled_by": b.cancelled_by}


# ---------------------------------------------------------------- testimonials (45)

def add_testimonial(db: Session, customer: User, booking_id: uuid.UUID, rating: int, text: str) -> Testimonial:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.customer_id != customer.id:
        raise AppError(404, "not_found")
    if booking.status != "completed":
        raise AppError(409, "booking_not_completed")
    if db.execute(select(Testimonial.id).where(Testimonial.booking_id == booking.id)).first():
        raise AppError(409, "already_reviewed")
    testimonial = Testimonial(booking_id=booking.id, profile_id=booking.profile_id, customer_id=customer.id, rating=rating, text=text)
    db.add(testimonial)
    db.flush()
    recompute_rating(db, booking.profile_id)
    from app.modules.rewards.service import award

    award(db, customer.id, "testimonial", ref=str(booking.id))
    return testimonial


def recompute_rating(db: Session, profile_id: uuid.UUID) -> None:
    avg, count = db.execute(select(func.avg(Testimonial.rating), func.count()).where(
        Testimonial.profile_id == profile_id, Testimonial.status == "published")).one()
    profile = db.get(StylistProfile, profile_id)
    profile.rating_avg, profile.rating_count = float(avg or 0), int(count)
    db.flush()
