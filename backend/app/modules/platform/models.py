from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, IdMixin, TimestampMixin


class PlatformSetting(Base, IdMixin, TimestampMixin):
    """A policy value the client still has to decide (Feature List rows 61-66),
    kept as data so it can change without a release."""

    __tablename__ = "platform_settings"
    key: Mapped[str] = mapped_column(String(80), unique=True)
    value: Mapped[dict | list | int | float | bool | str] = mapped_column(JSONB)
    description: Mapped[str] = mapped_column(String(400), default="")


class Country(Base, IdMixin, TimestampMixin):
    """Where the service is offered (rows 3 and 52)."""

    __tablename__ = "countries"
    code: Mapped[str] = mapped_column(String(2), unique=True)  # ISO 3166-1 alpha-2
    name: Mapped[dict] = mapped_column(JSONB)
    currency: Mapped[str] = mapped_column(String(3))
    is_launch_market: Mapped[bool] = mapped_column(Boolean, default=False)  # UAE
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # takes effect only with international_expansion
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
