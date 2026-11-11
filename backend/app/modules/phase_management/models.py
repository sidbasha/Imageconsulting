import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Identity, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin


class ApplicationPhase(Base, IdMixin, TimestampMixin):
    __tablename__ = "application_phases"
    key: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    sort_order: Mapped[int] = mapped_column(Integer)


class FeatureModule(Base, IdMixin, TimestampMixin):
    __tablename__ = "feature_modules"
    key: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(160))


class FeatureFlag(Base, IdMixin, TimestampMixin):
    """Catalog entry for one feature. Its on/off state is NOT stored here: the
    active release configuration is the only source of release state."""

    __tablename__ = "feature_flags"
    key: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    phase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application_phases.id", ondelete="RESTRICT"), index=True)
    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feature_modules.id", ondelete="RESTRICT"), index=True)
    source_row: Mapped[int | None] = mapped_column(Integer)  # S.No in the client's Excel
    source_phase_label: Mapped[str | None] = mapped_column(String(60))  # Excel "Suggested phase" verbatim
    is_enhancement: Mapped[bool] = mapped_column(Boolean, default=False)
    phase: Mapped[ApplicationPhase] = relationship(lazy="joined")
    module: Mapped[FeatureModule] = relationship(lazy="joined")


class FeatureDependency(Base, IdMixin, TimestampMixin):
    __tablename__ = "feature_dependencies"
    __table_args__ = (UniqueConstraint("feature_id", "requires_feature_id"),)
    feature_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feature_flags.id", ondelete="CASCADE"), index=True)
    requires_feature_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feature_flags.id", ondelete="CASCADE"), index=True
    )
    basis: Mapped[str] = mapped_column(String(20))  # excel | mom | proposed
    reason: Mapped[str] = mapped_column(String(255))
    feature: Mapped[FeatureFlag] = relationship(foreign_keys=[feature_id], lazy="joined")
    requires: Mapped[FeatureFlag] = relationship(foreign_keys=[requires_feature_id], lazy="joined")


class ReleaseConfiguration(Base, IdMixin, TimestampMixin):
    """One release. `snapshot` is the complete, immutable phase/feature state
    and is set when the release becomes active. `changes` is the delta the
    Super Admin asked for; a scheduled release keeps only the delta until due."""

    __tablename__ = "release_configurations"
    __table_args__ = (
        Index(
            "uq_release_configurations_one_active",
            "status",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )
    version: Mapped[int] = mapped_column(Integer, Identity(), unique=True)
    status: Mapped[str] = mapped_column(String(20), index=True)  # active|scheduled|superseded|failed|cancelled
    note: Mapped[str] = mapped_column(Text)
    changes: Mapped[dict | None] = mapped_column(JSONB)
    snapshot: Mapped[dict | None] = mapped_column(JSONB)
    activate_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    restored_from_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("release_configurations.id", ondelete="SET NULL")
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class ReleaseHistory(Base, IdMixin):
    """Append-only audit trail of release actions."""

    __tablename__ = "release_history"
    release_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("release_configurations.id", ondelete="CASCADE"), index=True
    )
    previous_release_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("release_configurations.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(20))  # seeded|activated|scheduled|rolled_back|failed|cancelled
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    detail: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
