import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin

# Text shown to users is stored per language as {"en": "...", "ar": "..."}.
# Adding a language means adding a key; no schema change.


class Questionnaire(Base, IdMixin, TimestampMixin):
    __tablename__ = "questionnaires"
    key: Mapped[str] = mapped_column(String(60), unique=True)
    feature_key: Mapped[str] = mapped_column(String(80))  # release switch that exposes it
    title: Mapped[dict] = mapped_column(JSONB)
    intro: Mapped[dict] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    content_status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | approved
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    questions: Mapped[list["Question"]] = relationship(
        order_by="Question.sort_order", cascade="all, delete-orphan", lazy="selectin"
    )
    profiles: Mapped[list["ResultProfile"]] = relationship(
        order_by="ResultProfile.sort_order", cascade="all, delete-orphan", lazy="selectin"
    )


class Question(Base, IdMixin, TimestampMixin):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("questionnaire_id", "key"),)
    questionnaire_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questionnaires.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(60))
    prompt: Mapped[dict] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    options: Mapped[list["QuestionOption"]] = relationship(
        order_by="QuestionOption.sort_order", cascade="all, delete-orphan", lazy="selectin"
    )


class QuestionOption(Base, IdMixin, TimestampMixin):
    __tablename__ = "question_options"
    __table_args__ = (UniqueConstraint("question_id", "key"),)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(60))
    label: Mapped[dict] = mapped_column(JSONB)
    image_key: Mapped[str | None] = mapped_column(String(255))  # for image-based choices, once supplied
    scores: Mapped[dict] = mapped_column(JSONB, default=dict)  # {profile_key: weight}
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ResultProfile(Base, IdMixin, TimestampMixin):
    """A possible outcome of a questionnaire, with the advice attached to it."""

    __tablename__ = "result_profiles"
    __table_args__ = (UniqueConstraint("questionnaire_id", "key"),)
    questionnaire_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questionnaires.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(60))
    title: Mapped[dict] = mapped_column(JSONB)
    summary: Mapped[dict] = mapped_column(JSONB)
    advice: Mapped[dict] = mapped_column(JSONB, default=dict)  # {category: {"en": [...], "ar": [...]}}
    palette: Mapped[list | None] = mapped_column(JSONB)  # hex colours, for colour results
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Assessment(Base, IdMixin):
    """One completed questionnaire. Retaking adds a row; history is kept."""

    __tablename__ = "assessments"
    __table_args__ = (Index("ix_assessments_user_questionnaire_created", "user_id", "questionnaire_id", "created_at"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    questionnaire_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questionnaires.id", ondelete="RESTRICT"))
    answers: Mapped[dict] = mapped_column(JSONB)  # {question_key: option_key}
    scores: Mapped[dict] = mapped_column(JSONB)  # {profile_key: total}
    profile_key: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AssessmentImage(Base, IdMixin, TimestampMixin):
    """A user photo. The file itself lives in private storage under storage_key."""

    __tablename__ = "assessment_images"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # face | full_body
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(40))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    quality: Mapped[dict] = mapped_column(JSONB)  # measurements taken by the quality gate
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # when the user agreed to processing
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
