import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, IdMixin, TimestampMixin


class CustomerProfile(Base, IdMixin, TimestampMixin):
    """Facts needed for eligibility (rows 2, 3). Self-declared unless
    identity_status is "verified", in which case they came from the verification."""

    __tablename__ = "customer_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(10))  # female | male
    country_code: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(20))
    eligibility_status: Mapped[str] = mapped_column(String(20), default="incomplete")  # incomplete|eligible|ineligible|pending_review
    eligibility_reasons: Mapped[list] = mapped_column(JSONB, default=list)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    identity_status: Mapped[str] = mapped_column(String(20), default="unverified")  # unverified|pending|verified|rejected


class IdentityVerification(Base, IdMixin, TimestampMixin):
    """One attempt to verify identity (row 1): UAE Pass or an ID document upload."""

    __tablename__ = "identity_verifications"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    method: Mapped[str] = mapped_column(String(20))  # uae_pass | id_document
    status: Mapped[str] = mapped_column(String(20))  # pending | verified | rejected
    # Private storage keys of uploaded document images; emptied once reviewed if the policy says so.
    document_keys: Mapped[list] = mapped_column(JSONB, default=list)
    # Only what eligibility needs is kept from the provider: no ID number.
    claims: Mapped[dict] = mapped_column(JSONB, default=dict)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String(300))
