import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, IdMixin, TimestampMixin


class Campaign(Base, IdMixin, TimestampMixin):
    """Paid visibility (rows 42, 49, 50), managed in the admin (row 60).

    A stylist campaign features her in discovery; a brand campaign shows a
    banner or offer card. Geo targeting applies when location-targeted
    promotions (row 50) is released.
    """

    __tablename__ = "campaigns"
    advertiser_type: Mapped[str] = mapped_column(String(10))  # stylist | brand
    profile_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stylist_profiles.id", ondelete="CASCADE"))
    advertiser_name: Mapped[str] = mapped_column(String(120))
    placement: Mapped[str] = mapped_column(String(30))  # discovery_featured | home_banner | offers
    title: Mapped[dict] = mapped_column(JSONB, default=dict)
    body: Mapped[dict] = mapped_column(JSONB, default=dict)
    image_url: Mapped[str | None] = mapped_column(String(500))
    target_url: Mapped[str | None] = mapped_column(String(500))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # pending_payment | pending_review | active | rejected | cancelled
    status: Mapped[str] = mapped_column(String(20))
    price_minor: Mapped[int] = mapped_column(Integer, default=0)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    radius_km: Mapped[float | None] = mapped_column(Float)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)


class Voucher(Base, IdMixin, TimestampMixin):
    """A partner offer users can claim (row 51)."""

    __tablename__ = "vouchers"
    partner_name: Mapped[str] = mapped_column(String(120))
    title: Mapped[dict] = mapped_column(JSONB)
    terms: Mapped[dict] = mapped_column(JSONB, default=dict)
    code: Mapped[str] = mapped_column(String(40))  # the partner's code, shown once claimed
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    max_claims: Mapped[int | None] = mapped_column(Integer)
    claimed: Mapped[int] = mapped_column(Integer, default=0)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    radius_km: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(default=True)


class VoucherClaim(Base, IdMixin, TimestampMixin):
    __tablename__ = "voucher_claims"
    __table_args__ = (UniqueConstraint("voucher_id", "user_id"),)
    voucher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vouchers.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
