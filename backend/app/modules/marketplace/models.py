import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin


class StylistProfile(Base, IdMixin, TimestampMixin):
    """A consultant's application and, once approved, her public profile (rows 15, 17, 18)."""

    __tablename__ = "stylist_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    bio: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str | None] = mapped_column(String(80))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    languages: Mapped[list] = mapped_column(JSONB, default=list)
    specialities: Mapped[list] = mapped_column(JSONB, default=list)
    years_experience: Mapped[int | None] = mapped_column(Integer)
    business_license_no: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|submitted|approved|rejected|suspended
    review_note: Mapped[str | None] = mapped_column(String(500))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)


class Credential(Base, IdMixin, TimestampMixin):
    """Supporting evidence for an application (row 16), reviewed one by one (row 54)."""

    __tablename__ = "stylist_credentials"
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stylist_profiles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # certification|practice_evidence|invoice|testimonial|referral|business_license
    title: Mapped[str] = mapped_column(String(160))
    storage_key: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|accepted|rejected
    note: Mapped[str | None] = mapped_column(String(300))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StylistService(Base, IdMixin, TimestampMixin):
    """Something a stylist offers, with her price (rows 18-24, 46)."""

    __tablename__ = "stylist_services"
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stylist_profiles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    price_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="AED")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    mode: Mapped[str] = mapped_column(String(10), default="online")  # online | in_person
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    profile: Mapped[StylistProfile] = relationship(lazy="joined")


class AvailabilitySlot(Base, IdMixin, TimestampMixin):
    __tablename__ = "availability_slots"
    __table_args__ = (UniqueConstraint("profile_id", "starts_at"),)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stylist_profiles.id", ondelete="CASCADE"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    booking_id: Mapped[uuid.UUID | None] = mapped_column()  # set while held or booked


class Booking(Base, IdMixin, TimestampMixin):
    __tablename__ = "bookings"
    __table_args__ = (Index("ix_bookings_customer_created", "customer_id", "created_at"),)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stylist_profiles.id", ondelete="RESTRICT"), index=True)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stylist_services.id", ondelete="RESTRICT"))
    slot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("availability_slots.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(30))  # copied from the service
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # pending_payment | confirmed | completed | cancelled | expired
    status: Mapped[str] = mapped_column(String(20), default="pending_payment")
    price_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    paid_with: Mapped[str | None] = mapped_column(String(20))  # payment | reward
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    address: Mapped[dict | None] = mapped_column(JSONB)  # in-person services (row 46)
    cancelled_by: Mapped[str | None] = mapped_column(String(20))  # customer | stylist | system
    service: Mapped[StylistService] = relationship(lazy="joined")
    profile: Mapped[StylistProfile] = relationship(lazy="joined")


class Testimonial(Base, IdMixin, TimestampMixin):
    """Feedback after a completed booking (row 45). One per booking."""

    __tablename__ = "testimonials"
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), unique=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stylist_profiles.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="published")  # published | hidden
