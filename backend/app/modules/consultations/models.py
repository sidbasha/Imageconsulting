import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, IdMixin, TimestampMixin


class Consultation(Base, IdMixin, TimestampMixin):
    """The work behind a confirmed booking (row 20): intake, files, the expert report."""

    __tablename__ = "consultations"
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stylist_profiles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | delivered
    intake: Mapped[dict] = mapped_column(JSONB, default=dict)


class ConsultationFile(Base, IdMixin, TimestampMixin):
    """A photo the customer added for the stylist: outfit, wardrobe, product or her face."""

    __tablename__ = "consultation_files"
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(20))  # outfit | wardrobe | product | face
    storage_key: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(40))
    caption: Mapped[str | None] = mapped_column(String(300))
    verdict: Mapped[dict | None] = mapped_column(JSONB)  # the stylist's call on this item (row 23)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReportTemplate(Base, IdMixin, TimestampMixin):
    """Standard expert report layout per service (rows 25, 56).

    sections: [{"key", "title": {en, ar}, "type": decision|text|list|choice|palette, "options": [...], "required": bool}]
    """

    __tablename__ = "report_templates"
    key: Mapped[str] = mapped_column(String(60), unique=True)
    service_kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[dict] = mapped_column(JSONB)
    sections: Mapped[list] = mapped_column(JSONB)
    content_status: Mapped[str] = mapped_column(String(20), default="draft")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ExpertReport(Base, IdMixin, TimestampMixin):
    __tablename__ = "expert_reports"
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id", ondelete="CASCADE"), unique=True)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("report_templates.id", ondelete="RESTRICT"))
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | delivered
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkspaceAccess(Base, IdMixin, TimestampMixin):
    """A consultant opened the colour workspace for a client (rows 27, 29). One
    row per consultant and client: metering charges once per client."""

    __tablename__ = "workspace_access"
    __table_args__ = (UniqueConstraint("profile_id", "customer_id"),)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stylist_profiles.id", ondelete="CASCADE"))
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    credits_used: Mapped[int] = mapped_column(default=0)


class DrapingSession(Base, IdMixin, TimestampMixin):
    """One guided draping analysis of a client's face photo (consultations/draping.py).

    choices: [{"step", "pair", "pick"}]; result fields fill in when the consultant
    confirms a type. custom_palette lets the consultant adjust the client's palette.
    """

    __tablename__ = "draping_sessions"
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stylist_profiles.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consultation_files.id", ondelete="SET NULL"))
    choices: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # in_progress | complete
    axes: Mapped[dict | None] = mapped_column(JSONB)
    scores: Mapped[list | None] = mapped_column(JSONB)
    colour_type: Mapped[str | None] = mapped_column(String(30))
    custom_palette: Mapped[list | None] = mapped_column(JSONB)  # hex colours chosen by the consultant
    notes: Mapped[str | None] = mapped_column(String(2000))
