import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, IdMixin, TimestampMixin


class Thread(Base, IdMixin, TimestampMixin):
    """One conversation between a customer and a stylist (row 30)."""

    __tablename__ = "message_threads"
    __table_args__ = (UniqueConstraint("customer_id", "stylist_user_id"),)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    stylist_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Message(Base, IdMixin):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_thread_created", "thread_id", "created_at"),)
    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("message_threads.id", ondelete="CASCADE"))
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text)
    # delivered | blocked (never shown to the recipient) | released (blocked, then cleared by a moderator)
    status: Mapped[str] = mapped_column(String(20))
    flags: Mapped[list] = mapped_column(JSONB, default=list)  # [{"kind", "match"}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Violation(Base, IdMixin, TimestampMixin):
    """A detected attempt to share contact details (row 33)."""

    __tablename__ = "violations"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    kinds: Mapped[list] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | upheld | dismissed
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MessagingRestriction(Base, IdMixin, TimestampMixin):
    __tablename__ = "messaging_restrictions"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    warned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    banned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(String(300))
