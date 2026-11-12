"""Eligibility (row 2), launch-market access (row 3, 52), identity (row 1) and
the reviews behind them (row 53).

Eligibility is re-evaluated whenever the profile, a verification or a policy
setting it depends on is used. It never deletes anything: a user who stops
being eligible keeps her data and loses access until the cause is fixed.
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.integrations.storage import Storage
from app.integrations.uae_pass import UaePassProfile
from app.modules.auth.models import User
from app.modules.platform import service as platform
from app.modules.users.models import CustomerProfile, IdentityVerification

GENDERS = ("female", "male")
ID_TYPES = {"image/jpeg": "jpg", "image/png": "png", "application/pdf": "pdf"}
MAX_ID_BYTES = 8 * 1024 * 1024


def profile_for(db: Session, user: User) -> CustomerProfile:
    profile = db.execute(select(CustomerProfile).where(CustomerProfile.user_id == user.id)).scalar_one_or_none()
    if profile is None:
        profile = CustomerProfile(user_id=user.id, eligibility_reasons=[])
        db.add(profile)
        db.flush()
    return profile


def age_on(born: date, today: date) -> int:
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def evaluate(db: Session, profile: CustomerProfile, enabled: set[str], today: date | None = None) -> CustomerProfile:
    """Sets eligibility_status and the reasons behind it."""
    today = today or datetime.now(UTC).date()
    reasons = []
    if "phase1.eligibility_verification" in enabled:
        if profile.date_of_birth is None or profile.gender is None:
            reasons.append("profile_incomplete")
        else:
            if age_on(profile.date_of_birth, today) < platform.get(db, "eligibility.min_age"):
                reasons.append("under_minimum_age")
            if platform.get(db, "eligibility.women_only") and profile.gender != "female":
                reasons.append("women_only")
    if "phase1.uae_only_access" in enabled or "phase3.international_expansion" in enabled:
        allowed = {c.code for c in platform.available_countries(db, enabled)}
        if profile.country_code is None:
            reasons.append("profile_incomplete")
        elif profile.country_code not in allowed:
            reasons.append("country_not_available")
    reasons = sorted(set(reasons))

    if profile.reviewed_at is not None and profile.eligibility_status in ("eligible", "ineligible") and not reasons:
        return profile  # a reviewer's decision stands while the facts still allow it
    if "profile_incomplete" in reasons:
        status = "incomplete"
    elif reasons:
        status = "ineligible"
    elif platform.get(db, "eligibility.manual_review") and profile.reviewed_at is None:
        status = "pending_review"
    else:
        status = "eligible"
    profile.eligibility_status, profile.eligibility_reasons = status, reasons
    db.flush()
    return profile


def update_profile(db: Session, user: User, enabled: set[str], **fields) -> CustomerProfile:
    profile = profile_for(db, user)
    if profile.identity_status == "verified":
        # Verified facts come from the verification and cannot be self-edited.
        for locked in ("date_of_birth", "gender"):
            if fields.get(locked) is not None and fields[locked] != getattr(profile, locked):
                raise AppError(409, "verified_field_locked", {"field": locked})
    if fields.get("gender") is not None and fields["gender"] not in GENDERS:
        raise AppError(422, "invalid_profile", {"field": "gender"})
    if fields.get("date_of_birth") is not None and fields["date_of_birth"] > datetime.now(UTC).date():
        raise AppError(422, "invalid_profile", {"field": "date_of_birth"})
    for key, value in fields.items():
        if value is not None:
            setattr(profile, key, value.upper() if key == "country_code" else value)
    return evaluate(db, profile, enabled)


def require_eligible(db: Session, user: User, enabled: set[str]) -> None:
    """Customers must be eligible to use customer features. Staff and stylists are not customers."""
    if user.role.key != "customer":
        return
    if "phase1.eligibility_verification" not in enabled and "phase1.uae_only_access" not in enabled:
        return
    profile = evaluate(db, profile_for(db, user), enabled)
    if profile.eligibility_status != "eligible":
        raise AppError(403, "not_eligible", {"status": profile.eligibility_status, "reasons": profile.eligibility_reasons})


def require_verified_identity(db: Session, user: User, enabled: set[str]) -> None:
    """Identity is required before contact with stylists (booking, messaging), not for self-assessment."""
    if "phase1.identity_verification" not in enabled or user.role.key != "customer":
        return
    if profile_for(db, user).identity_status != "verified":
        raise AppError(403, "identity_not_verified")


# ---------------------------------------------------------------- identity

def verify_with_uae_pass(db: Session, user: User, result: UaePassProfile, enabled: set[str]) -> IdentityVerification:
    taken = db.execute(
        select(IdentityVerification).where(
            IdentityVerification.method == "uae_pass",
            IdentityVerification.status == "verified",
            IdentityVerification.claims["subject"].astext == result.subject,
            IdentityVerification.user_id != user.id,
        )
    ).first()
    if taken:
        raise AppError(409, "identity_already_used")
    claims = {
        "subject": result.subject,
        "gender": result.gender,
        "date_of_birth": result.date_of_birth and result.date_of_birth.isoformat(),
        "nationality": result.nationality,
    }
    record = IdentityVerification(
        user_id=user.id, method="uae_pass", status="verified", claims=claims, reviewed_at=datetime.now(UTC)
    )
    db.add(record)
    profile = profile_for(db, user)
    profile.identity_status = "verified"
    # Verified facts replace self-declared ones.
    if result.gender in GENDERS:
        profile.gender = result.gender
    if result.date_of_birth:
        profile.date_of_birth = result.date_of_birth
    evaluate(db, profile, enabled)
    return record


def submit_document(db: Session, storage: Storage, user: User, files: list[tuple[bytes, str]]) -> IdentityVerification:
    if not 1 <= len(files) <= 2:
        raise AppError(422, "invalid_document", {"expected": "front, and back if any"})
    record = IdentityVerification(id=uuid.uuid4(), user_id=user.id, method="id_document", status="pending", claims={})
    keys = []
    for data, content_type in files:
        if content_type not in ID_TYPES:
            raise AppError(415, "unsupported_document_type")
        if len(data) > MAX_ID_BYTES:
            raise AppError(413, "document_too_large")
        key = f"identity/{user.id}/{record.id}-{len(keys)}.{ID_TYPES[content_type]}"
        storage.put(key, data)
        keys.append(key)
    record.document_keys = keys
    db.add(record)
    profile_for(db, user).identity_status = "pending"
    db.flush()
    return record


def review_document(
    db: Session, storage: Storage, reviewer: User, record_id: uuid.UUID, *, approve: bool,
    reason: str | None, date_of_birth: date | None, gender: str | None, enabled: set[str],
) -> IdentityVerification:
    record = db.get(IdentityVerification, record_id)
    if record is None or record.method != "id_document":
        raise AppError(404, "not_found")
    if record.status != "pending":
        raise AppError(409, "already_reviewed")
    record.status = "verified" if approve else "rejected"
    record.reviewer_id, record.reviewed_at, record.reason = reviewer.id, datetime.now(UTC), reason
    user = db.get(User, record.user_id)
    profile = profile_for(db, user)
    profile.identity_status = record.status
    if approve:
        # The reviewer reads these off the document; they replace the self-declared values.
        if gender in GENDERS:
            profile.gender = gender
        if date_of_birth:
            profile.date_of_birth = date_of_birth
        record.claims = {"gender": profile.gender, "date_of_birth": profile.date_of_birth and profile.date_of_birth.isoformat()}
    # Row 65: keep ID images no longer than the review needs (default; see settings).
    if platform.get(db, "identity.delete_documents_after_review"):
        for key in record.document_keys:
            storage.delete(key)
        record.document_keys = []
    evaluate(db, profile, enabled)
    return record


def review_eligibility(db: Session, reviewer: User, user_id: uuid.UUID, approve: bool, enabled: set[str]) -> CustomerProfile:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "not_found")
    profile = profile_for(db, user)
    profile.reviewed_by, profile.reviewed_at = reviewer.id, datetime.now(UTC)
    profile.eligibility_status = "eligible" if approve else "ineligible"
    if not approve:
        profile.eligibility_reasons = sorted(set(profile.eligibility_reasons) | {"rejected_by_review"})
    return evaluate(db, profile, enabled)
