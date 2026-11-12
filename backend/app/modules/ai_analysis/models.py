import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, IdMixin


class PhotoAnalysis(Base, IdMixin):
    """One automated analysis of one photo. Re-running adds a row; history is kept.

    Results are indicative (see ai_analysis/shapes.py and colour.py) and are
    always shown with basis "photo_analysis", separate from expert results.
    """

    __tablename__ = "photo_analyses"
    __table_args__ = (Index("ix_photo_analyses_user_kind_created", "user_id", "kind", "created_at"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Kept when the photo is deleted: the result stays, the photo does not.
    image_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assessment_images.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(30))  # face_shape | body_shape | seasonal_color
    profile_key: Mapped[str] = mapped_column(String(60))
    confidence: Mapped[float] = mapped_column(Float)
    scores: Mapped[dict] = mapped_column(JSONB)
    measurements: Mapped[dict] = mapped_column(JSONB)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)  # axes, swatches
    notes: Mapped[list] = mapped_column(JSONB, default=list)
    model_version: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TryOnItem(Base, IdMixin):
    """A garment or hairstyle cut out of a reference photo, for try-on (rows 11, 12).

    Created by an administrator from a photo the client has the rights to use;
    hidden from customers until approved (content_status = approved).
    """

    __tablename__ = "tryon_items"
    kind: Mapped[str] = mapped_column(String(20))  # garment | hairstyle
    title: Mapped[dict] = mapped_column(JSONB)
    category: Mapped[str | None] = mapped_column(String(30))  # dress, top, outerwear... / short, medium, long
    source_key: Mapped[str] = mapped_column(String(255))  # the reference photo, private
    asset_key: Mapped[str] = mapped_column(String(255))  # the cut-out, PNG with transparency
    anchors: Mapped[dict] = mapped_column(JSONB)
    tags: Mapped[dict] = mapped_column(JSONB, default=dict)  # {"seasonal_color": [...], "face_shape": [...], ...}
    retail_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("retail_items.id", ondelete="SET NULL"))
    licence: Mapped[str] = mapped_column(String(300))  # who owns the reference photo and on what terms
    content_status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | approved
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
