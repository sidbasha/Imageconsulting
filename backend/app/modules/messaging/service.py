"""In-app messaging with contact-sharing safeguards (rows 30-33, 58).

Policy thresholds are settings (row 33: to be confirmed by the client).
Counting uses violations that are open or upheld; a dismissed one (a false
positive released by a moderator) does not count.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.auth.models import User
from app.modules.marketplace.models import Booking, StylistProfile
from app.modules.messaging.detection import scan
from app.modules.messaging.models import Message, MessagingRestriction, Thread, Violation
from app.modules.platform import service as platform

MAX_LENGTH = 4000


def now() -> datetime:
    return datetime.now(UTC)


def restriction(db: Session, user_id) -> MessagingRestriction:
    row = db.execute(select(MessagingRestriction).where(MessagingRestriction.user_id == user_id)).scalar_one_or_none()
    if row is None:
        row = MessagingRestriction(user_id=user_id)
        db.add(row)
        db.flush()
    return row


def can_send(db: Session, user: User) -> None:
    row = db.execute(select(MessagingRestriction).where(MessagingRestriction.user_id == user.id)).scalar_one_or_none()
    if row and row.banned_at:
        raise AppError(403, "messaging_banned")
    if row and row.suspended_until and row.suspended_until > now():
        raise AppError(403, "messaging_suspended", {"until": row.suspended_until.isoformat()})


def open_thread(db: Session, customer: User, profile_id: uuid.UUID) -> Thread:
    """Customers can message a stylist they have booked (keeps unsolicited contact out)."""
    profile = db.get(StylistProfile, profile_id)
    if profile is None or profile.status != "approved":
        raise AppError(404, "not_found")
    booked = db.execute(select(Booking.id).where(
        Booking.customer_id == customer.id, Booking.profile_id == profile.id,
        Booking.status.in_(("confirmed", "completed")))).first()
    if not booked:
        raise AppError(409, "booking_required")
    thread = db.execute(select(Thread).where(Thread.customer_id == customer.id, Thread.stylist_user_id == profile.user_id)).scalar_one_or_none()
    if thread is None:
        thread = Thread(customer_id=customer.id, stylist_user_id=profile.user_id)
        db.add(thread)
        db.flush()
    return thread


def thread_for(db: Session, user: User, thread_id: uuid.UUID) -> Thread:
    thread = db.get(Thread, thread_id)
    if thread is None or user.id not in (thread.customer_id, thread.stylist_user_id):
        raise AppError(404, "not_found")
    return thread


def send(db: Session, user: User, thread: Thread, body: str, enabled: set[str]) -> tuple[Message, dict | None]:
    can_send(db, user)
    body = body.strip()
    if not body or len(body) > MAX_LENGTH:
        raise AppError(422, "invalid_message")
    findings = scan(body) if "phase2.contact_detection" in enabled else []
    blocked = bool(findings) and "phase2.message_blocking" in enabled
    message = Message(thread_id=thread.id, sender_id=user.id, body=body,
                      status="blocked" if blocked else "delivered",
                      flags=[{"kind": f.kind, "match": f.match} for f in findings])
    db.add(message)
    thread.last_message_at = now()
    db.flush()
    warning = None
    if findings:
        warning = {"code": "contact_details_blocked" if blocked else "contact_details_flagged",
                   "kinds": sorted({f.kind for f in findings})}
        if "phase2.violation_tracking" in enabled:
            db.add(Violation(user_id=user.id, message_id=message.id, kinds=warning["kinds"]))
            db.flush()
            warning["consequence"] = apply_policy(db, user)
    return message, warning


def violation_count(db: Session, user_id) -> int:
    return int(db.scalar(select(func.count()).select_from(Violation).where(
        Violation.user_id == user_id, Violation.status.in_(("open", "upheld")))))


def apply_policy(db: Session, user: User) -> str:
    count = violation_count(db, user.id)
    row = restriction(db, user.id)
    if count >= platform.get(db, "moderation.ban_after"):
        row.banned_at = now()
        user.is_active = False  # account deactivated; data kept
        return "banned"
    if count >= platform.get(db, "moderation.suspend_after"):
        row.suspended_until = now() + timedelta(days=platform.get(db, "moderation.suspend_days"))
        return "suspended"
    if count >= platform.get(db, "moderation.warn_after"):
        row.warned_at = row.warned_at or now()
        return "warning"
    return "none"


def visible_messages(db: Session, user: User, thread: Thread) -> list[Message]:
    """Blocked messages are shown to their sender only, marked as not delivered."""
    rows = db.scalars(select(Message).where(Message.thread_id == thread.id,
                      or_(Message.status != "blocked", Message.sender_id == user.id)).order_by(Message.created_at))
    rows = list(rows)
    for m in rows:
        if m.sender_id != user.id and m.read_at is None:
            m.read_at = now()
    db.flush()
    return rows


def my_threads(db: Session, user: User) -> list[Thread]:
    return list(db.scalars(select(Thread).where(or_(Thread.customer_id == user.id, Thread.stylist_user_id == user.id))
                           .order_by(Thread.last_message_at.desc().nulls_last())))


# ---------------------------------------------------------------- moderation (58)

def review_violation(db: Session, moderator: User, violation_id: uuid.UUID, uphold: bool) -> Violation:
    violation = db.get(Violation, violation_id)
    if violation is None:
        raise AppError(404, "not_found")
    if violation.status != "open":
        raise AppError(409, "already_reviewed")
    violation.status = "upheld" if uphold else "dismissed"
    violation.reviewed_by, violation.reviewed_at = moderator.id, now()
    if not uphold:
        message = db.get(Message, violation.message_id)
        if message.status == "blocked":
            message.status = "released"  # false positive: deliver it after all
    db.flush()
    return violation


def lift(db: Session, user_id: uuid.UUID, note: str) -> MessagingRestriction:
    row = restriction(db, user_id)
    row.suspended_until, row.banned_at, row.note = None, None, note
    user = db.get(User, user_id)
    user.is_active = True
    db.flush()
    return row
