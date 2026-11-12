import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, func
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
