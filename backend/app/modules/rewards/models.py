import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, IdMixin, TimestampMixin


class RewardRule(Base, IdMixin, TimestampMixin):
    """Points for an engagement event (row 43). Managed in the admin (row 59)."""

    __tablename__ = "reward_rules"
    event: Mapped[str] = mapped_column(String(40), unique=True)
    points: Mapped[int] = mapped_column(Integer)
    max_per_day: Mapped[int | None] = mapped_column(Integer)  # caps repeatable events
    once_per_ref: Mapped[bool] = mapped_column(Boolean, default=True)  # e.g. one award per questionnaire
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[dict] = mapped_column(JSONB)


class RedemptionOption(Base, IdMixin, TimestampMixin):
    """What points can be exchanged for (row 44)."""

    __tablename__ = "redemption_options"
    key: Mapped[str] = mapped_column(String(60), unique=True)
    title: Mapped[dict] = mapped_column(JSONB)
    points_cost: Mapped[int] = mapped_column(Integer)
    grants: Mapped[str] = mapped_column(String(80))  # entitlement key
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PointsEntry(Base, IdMixin):
    """Append-only ledger; the balance is the sum."""

    __tablename__ = "points_ledger"
    __table_args__ = (Index("ix_points_ledger_user_created", "user_id", "created_at"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    delta: Mapped[int] = mapped_column(Integer)
    event: Mapped[str] = mapped_column(String(40))  # earning event, "redeem", or "adjustment"
    ref: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
