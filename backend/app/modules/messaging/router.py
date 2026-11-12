import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.database.session import get_db
from app.modules.auth.models import User
from app.modules.feature_flags.guard import enabled_features, require_feature
from app.modules.messaging import service
from app.modules.messaging.models import Message, MessagingRestriction, Thread, Violation
from app.modules.users.deps import verified_user

router = APIRouter(prefix="/messages", tags=["messages"], dependencies=[Depends(require_feature("phase2.messaging"))])


def message_out(m: Message, me: uuid.UUID) -> dict:
    return {"id": m.id, "mine": m.sender_id == me, "body": m.body, "created_at": m.created_at,
            "status": "not_delivered" if m.status == "blocked" else "delivered", "read": m.read_at is not None}


def thread_out(db: Session, t: Thread, me: User) -> dict:
    other = db.get(User, t.stylist_user_id if t.customer_id == me.id else t.customer_id)
    unread = db.scalar(select(Message.id).where(Message.thread_id == t.id, Message.sender_id != me.id,
                                                 Message.read_at.is_(None), Message.status != "blocked").limit(1))
    return {"id": t.id, "with": {"id": other.id, "name": other.full_name}, "last_message_at": t.last_message_at, "unread": bool(unread)}


@router.get("")
def threads(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    return [thread_out(db, t, user) for t in service.my_threads(db, user)]


class OpenIn(BaseModel):
    stylist_id: uuid.UUID


@router.post("", status_code=status.HTTP_201_CREATED)
def open_thread(body: OpenIn, user: User = Depends(verified_user), db: Session = Depends(get_db)) -> dict:
    return thread_out(db, service.open_thread(db, user, body.stylist_id), user)


@router.get("/{thread_id}")
def messages(thread_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    thread = service.thread_for(db, user, thread_id)
    return [message_out(m, user.id) for m in service.visible_messages(db, user, thread)]


class SendIn(BaseModel):
    body: str = Field(min_length=1, max_length=service.MAX_LENGTH)


@router.post("/{thread_id}", status_code=status.HTTP_201_CREATED)
def send(thread_id: uuid.UUID, body: SendIn, user: User = Depends(get_current_user), db: Session = Depends(get_db),
         on: set[str] = Depends(enabled_features)) -> dict:
    thread = service.thread_for(db, user, thread_id)
    message, warning = service.send(db, user, thread, body.body, on)
    return {"message": message_out(message, user.id), "warning": warning}


admin = APIRouter(prefix="/admin/moderation", tags=["admin: moderation"])


@admin.get("/violations")
def violations(status_filter: str = "open", _: User = Depends(require_permission("moderation.manage")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(Violation, Message, User).join(Message, Message.id == Violation.message_id)
                      .join(User, User.id == Violation.user_id).where(Violation.status == status_filter)
                      .order_by(Violation.created_at)).all()
    return [{"id": v.id, "user": {"id": u.id, "name": u.full_name, "email": u.email}, "kinds": v.kinds,
             "message": m.body, "flags": m.flags, "message_status": m.status, "created_at": v.created_at,
             "user_violations": service.violation_count(db, u.id)} for v, m, u in rows]


class ReviewIn(BaseModel):
    uphold: bool


@admin.post("/violations/{violation_id}")
def review(violation_id: uuid.UUID, body: ReviewIn, moderator: User = Depends(require_permission("moderation.manage")), db: Session = Depends(get_db)) -> dict:
    v = service.review_violation(db, moderator, violation_id, body.uphold)
    return {"id": v.id, "status": v.status}


@admin.get("/restrictions")
def restrictions(_: User = Depends(require_permission("moderation.manage")), db: Session = Depends(get_db)) -> list[dict]:
    return [{"user_id": r.user_id, "warned_at": r.warned_at, "suspended_until": r.suspended_until, "banned_at": r.banned_at, "note": r.note}
            for r in db.scalars(select(MessagingRestriction).where(
                (MessagingRestriction.suspended_until > datetime.now().astimezone()) | MessagingRestriction.banned_at.is_not(None)))]


class LiftIn(BaseModel):
    note: str = Field(min_length=3, max_length=300)


@admin.post("/users/{user_id}/lift")
def lift(user_id: uuid.UUID, body: LiftIn, _: User = Depends(require_permission("moderation.manage")), db: Session = Depends(get_db)) -> dict:
    row = service.lift(db, user_id, body.note)
    return {"user_id": row.user_id, "suspended_until": row.suspended_until, "banned_at": row.banned_at}
