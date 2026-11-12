import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin

# Money is integer minor units (fils for AED) with an ISO currency code.


class Product(Base, IdMixin, TimestampMixin):
    """Something sold or given once: a digital guide, a report, a physical item,
    a pack of workspace credits (rows 37, 38, 39, 48, 29). Managed in the admin (row 57)."""

    __tablename__ = "products"
    key: Mapped[str] = mapped_column(String(80), unique=True)
    kind: Mapped[str] = mapped_column(String(30))  # guide | report | physical | workspace_credits
    feature_key: Mapped[str] = mapped_column(String(80))  # release switch that exposes it
    title: Mapped[dict] = mapped_column(JSONB)
    description: Mapped[dict] = mapped_column(JSONB)
    price_minor: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="AED")
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)  # complimentary resource (row 39)
    grants: Mapped[list] = mapped_column(JSONB, default=list)  # entitlement keys given on purchase
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)  # e.g. {"document": "seasonal_palette", "season": "spring"}
    requires_shipping: Mapped[bool] = mapped_column(Boolean, default=False)
    content_status: Mapped[str] = mapped_column(String(20), default="draft")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Plan(Base, IdMixin, TimestampMixin):
    """A recurring plan for customers (row 35) or consultants (row 40). Row 61:
    billing structure (annual billed monthly vs. separate plans) is undecided;
    each plan here bills its whole price once per interval."""

    __tablename__ = "plans"
    key: Mapped[str] = mapped_column(String(80), unique=True)
    audience: Mapped[str] = mapped_column(String(20))  # customer | consultant
    title: Mapped[dict] = mapped_column(JSONB)
    description: Mapped[dict] = mapped_column(JSONB)
    price_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="AED")
    interval: Mapped[str] = mapped_column(String(10))  # month | year
    grants: Mapped[list] = mapped_column(JSONB, default=list)
    content_status: Mapped[str] = mapped_column(String(20), default="draft")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Order(Base, IdMixin, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_user_created", "user_id", "created_at"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(30))  # product | plan | renewal | booking | promotion
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | paid | failed | cancelled | refunded
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    items: Mapped[list] = mapped_column(JSONB, default=list)  # [{key, title, quantity, unit_minor}]
    target_id: Mapped[uuid.UUID | None] = mapped_column()  # plan, subscription, booking or campaign
    provider: Mapped[str | None] = mapped_column(String(30))
    provider_ref: Mapped[str | None] = mapped_column(String(80), unique=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refund_ref: Mapped[str | None] = mapped_column(String(80))
    shipping: Mapped[dict | None] = mapped_column(JSONB)  # physical products (row 48)
    fulfilment_status: Mapped[str | None] = mapped_column(String(20))  # unfulfilled | shipped | delivered
    points_used: Mapped[int] = mapped_column(Integer, default=0)


class Subscription(Base, IdMixin, TimestampMixin):
    __tablename__ = "subscriptions"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | active | past_due | cancelled | expired
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    plan: Mapped[Plan] = relationship(lazy="joined")


class Entitlement(Base, IdMixin, TimestampMixin):
    """What a user may access (row 34). Granted by purchases, plans, free claims or rewards."""

    __tablename__ = "entitlements"
    __table_args__ = (Index("ix_entitlements_user_key", "user_id", "key"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(20))  # purchase | subscription | free | reward | admin
    source_id: Mapped[uuid.UUID | None] = mapped_column()
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quantity: Mapped[int] = mapped_column(Integer, default=1)  # countable grants, e.g. workspace credits


class RetailItem(Base, IdMixin, TimestampMixin):
    """A link to clothing on a retailer's site or app (row 36). Tags say which
    results it suits; matching is by tag overlap."""

    __tablename__ = "retail_items"
    retailer: Mapped[str] = mapped_column(String(80))
    title: Mapped[dict] = mapped_column(JSONB)
    url: Mapped[str] = mapped_column(String(500))
    image_url: Mapped[str | None] = mapped_column(String(500))
    price_text: Mapped[str | None] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(30), default="outfits")
    tags: Mapped[dict] = mapped_column(JSONB, default=dict)  # {"seasonal_color": ["spring"], "body_shape": [...], ...}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    clicks: Mapped[int] = mapped_column(Integer, default=0)


class RetailClick(Base, IdMixin):
    __tablename__ = "retail_clicks"
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("retail_items.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
