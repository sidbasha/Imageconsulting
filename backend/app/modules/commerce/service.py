"""Orders, payments, entitlements and subscriptions.

Other modules plug into payment completion through `on_paid`: bookings
confirm, promotions start, workspace credits are added. That keeps the
payment path single: every paid thing goes through an Order.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.integrations.payments import InvalidSignature, PaymentProvider
from app.modules.auth.models import User
from app.modules.commerce import content
from app.modules.commerce.models import Entitlement, Order, Plan, Product, Subscription

# kind -> callback(db, order). Registered by the modules that sell things.
ON_PAID: dict[str, Callable[[Session, Order], None]] = {}
ON_REFUNDED: dict[str, Callable[[Session, Order], None]] = {}
# Called after any paid order (rewards hooks in here).
AFTER_PAID: list[Callable[[Session, Order], None]] = []

PRODUCT_FEATURE_NEEDS = {"phase1.free_paid_access"}


def now() -> datetime:
    return datetime.now(UTC)


def seed(db: Session) -> None:
    keys = set(db.scalars(select(Product.key)))
    for order, spec in enumerate(content.PRODUCTS):
        if spec["key"] not in keys:
            db.add(Product(sort_order=order, **spec))
    plan_keys = set(db.scalars(select(Plan.key)))
    for order, spec in enumerate(content.PLANS):
        if spec["key"] not in plan_keys:
            db.add(Plan(sort_order=order, **spec))
    db.flush()


# ---------------------------------------------------------------- entitlements

def active_entitlements(db: Session, user: User) -> list[Entitlement]:
    return list(
        db.scalars(
            select(Entitlement).where(
                Entitlement.user_id == user.id,
                Entitlement.revoked_at.is_(None),
                or_(Entitlement.expires_at.is_(None), Entitlement.expires_at > now()),
            )
        )
    )


def has_entitlement(db: Session, user: User, key: str) -> bool:
    keys = {e.key for e in active_entitlements(db, user)}
    if key in keys:
        return True
    # Premium membership covers every guide and report.
    return content.PREMIUM in keys and (key.startswith("guide.") or key.startswith("report."))


def grant(db: Session, user_id: uuid.UUID, key: str, source: str, source_id=None, expires_at=None, quantity: int = 1) -> Entitlement:
    entitlement = Entitlement(user_id=user_id, key=key, source=source, source_id=source_id, expires_at=expires_at, quantity=quantity)
    db.add(entitlement)
    db.flush()
    return entitlement


def credit_balance(db: Session, user: User, key: str) -> int:
    return int(sum(e.quantity for e in active_entitlements(db, user) if e.key == key))


def consume_credit(db: Session, user: User, key: str, amount: int = 1) -> None:
    """Uses countable grants, oldest first, by adding a negative grant."""
    if credit_balance(db, user, key) < amount:
        raise AppError(402, "insufficient_credits", {"needed": amount})
    grant(db, user.id, key, "usage", quantity=-amount)


# ---------------------------------------------------------------- orders

def _checkout(db: Session, payments: PaymentProvider, order: Order, description: str) -> dict:
    checkout = payments.create_checkout(
        order_id=str(order.id), amount_minor=order.amount_minor, currency=order.currency, description=description
    )
    order.provider, order.provider_ref = payments.name, checkout.reference
    db.flush()
    return {"order_id": order.id, "status": order.status, "amount_minor": order.amount_minor,
            "currency": order.currency, "provider": payments.name, "payment_url": checkout.redirect_url}


def create_order(db: Session, payments: PaymentProvider, user: User, *, kind: str, amount_minor: int, currency: str,
                 items: list[dict], description: str, target_id=None, shipping=None, points_used: int = 0) -> dict:
    order = Order(user_id=user.id, kind=kind, amount_minor=amount_minor, currency=currency, items=items,
                  target_id=target_id, shipping=shipping, points_used=points_used,
                  fulfilment_status="unfulfilled" if shipping else None)
    db.add(order)
    db.flush()
    if amount_minor == 0:
        # Fully covered (e.g. by reward points): nothing to collect.
        mark_paid(db, order)
        return {"order_id": order.id, "status": order.status, "amount_minor": 0, "currency": currency,
                "provider": None, "payment_url": None}
    return _checkout(db, payments, order, description)


def buy_product(db: Session, payments: PaymentProvider, user: User, product: Product, quantity: int,
                shipping: dict | None, language: str) -> dict:
    if product.is_free:
        raise AppError(409, "product_is_free")
    if product.requires_shipping and not shipping:
        raise AppError(422, "shipping_required")
    if product.kind in ("guide", "report") and has_entitlement(db, user, product.key):
        raise AppError(409, "already_owned")
    quantity = quantity if product.kind in ("physical", "workspace_credits") else 1
    items = [{"key": product.key, "title": product.title.get(language) or product.title["en"],
              "quantity": quantity, "unit_minor": product.price_minor}]
    return create_order(db, payments, user, kind="product", amount_minor=product.price_minor * quantity,
                        currency=product.currency, items=items, description=items[0]["title"],
                        target_id=product.id, shipping=shipping if product.requires_shipping else None)


def subscribe(db: Session, payments: PaymentProvider, user: User, plan: Plan, language: str) -> dict:
    live = db.execute(
        select(Subscription).join(Plan).where(
            Subscription.user_id == user.id, Plan.audience == plan.audience,
            Subscription.status.in_(("active", "past_due")),
        )
    ).first()
    if live:
        raise AppError(409, "already_subscribed")
    subscription = Subscription(user_id=user.id, plan_id=plan.id, status="pending")
    db.add(subscription)
    db.flush()
    title = plan.title.get(language) or plan.title["en"]
    return create_order(db, payments, user, kind="plan", amount_minor=plan.price_minor, currency=plan.currency,
                        items=[{"key": plan.key, "title": title, "quantity": 1, "unit_minor": plan.price_minor}],
                        description=title, target_id=subscription.id)


def _period(start: datetime, interval: str) -> datetime:
    return start + (timedelta(days=365) if interval == "year" else timedelta(days=30))


def _activate_subscription(db: Session, order: Order) -> None:
    subscription = db.get(Subscription, order.target_id)
    start = max(subscription.current_period_end or now(), now())
    subscription.status = "active"
    subscription.current_period_start = start
    subscription.current_period_end = _period(start, subscription.plan.interval)
    # One grant per plan entitlement, valid to the end of the paid period.
    for key in subscription.plan.grants:
        grant(db, subscription.user_id, key, "subscription", subscription.id, subscription.current_period_end)


def _fulfil_product(db: Session, order: Order) -> None:
    product = db.get(Product, order.target_id)
    for key in product.grants:
        grant(db, order.user_id, key, "purchase", order.id)
    if product.kind == "workspace_credits":
        credits = int(product.payload.get("credits", 0)) * order.items[0]["quantity"]
        grant(db, order.user_id, "workspace.credits", "purchase", order.id, quantity=credits)


ON_PAID["plan"] = _activate_subscription
ON_PAID["renewal"] = _activate_subscription
ON_PAID["product"] = _fulfil_product


def mark_paid(db: Session, order: Order) -> None:
    if order.status == "paid":
        return  # webhooks can arrive twice
    if order.status != "pending":
        raise AppError(409, "order_not_payable")
    order.status, order.paid_at = "paid", now()
    db.flush()
    if order.kind in ON_PAID:
        ON_PAID[order.kind](db, order)
    if order.status == "paid":  # a fulfilment hook may have marked it refund_due
        for hook in AFTER_PAID:
            hook(db, order)
    db.flush()


def handle_webhook(db: Session, payments: PaymentProvider, body: bytes, headers: dict[str, str]) -> Order:
    try:
        event = payments.parse_webhook(body, headers)
    except (InvalidSignature, KeyError, ValueError) as exc:
        raise AppError(400, "invalid_webhook") from exc
    order = db.execute(
        select(Order).where(Order.provider == payments.name, Order.provider_ref == event.reference).with_for_update()
    ).scalar_one_or_none()
    if order is None:
        raise AppError(404, "not_found")
    if event.amount_minor != order.amount_minor or event.currency != order.currency:
        raise AppError(400, "invalid_webhook", {"reason": "amount mismatch"})
    if event.status == "paid":
        mark_paid(db, order)
    elif event.status == "failed" and order.status == "pending":
        order.status = "failed"
        db.flush()
    return order


def refund(db: Session, payments: PaymentProvider, order: Order) -> Order:
    if order.status not in ("paid", "refund_due"):
        raise AppError(409, "order_not_refundable")
    if order.amount_minor > 0 and order.provider_ref:
        order.refund_ref = payments.refund(reference=order.provider_ref, amount_minor=order.amount_minor)
    order.status, order.refunded_at = "refunded", now()
    # Take back what the order gave.
    for entitlement in db.scalars(select(Entitlement).where(Entitlement.source_id.in_([order.id, order.target_id]), Entitlement.revoked_at.is_(None))):
        if entitlement.user_id == order.user_id and entitlement.source in ("purchase", "subscription"):
            entitlement.revoked_at = now()
    if order.kind in ("plan", "renewal"):
        subscription = db.get(Subscription, order.target_id)
        subscription.status = "cancelled"
    if order.kind in ON_REFUNDED:
        ON_REFUNDED[order.kind](db, order)
    db.flush()
    return order


# ---------------------------------------------------------------- subscriptions

def cancel_subscription(db: Session, user: User, subscription_id: uuid.UUID) -> Subscription:
    subscription = db.get(Subscription, subscription_id)
    if subscription is None or subscription.user_id != user.id:
        raise AppError(404, "not_found")
    if subscription.status not in ("active", "past_due"):
        raise AppError(409, "subscription_not_active")
    # Access continues to the end of the period already paid for.
    subscription.cancel_at_period_end = True
    db.flush()
    return subscription


def renew_due(db: Session, payments: PaymentProvider, at: datetime | None = None) -> dict:
    """Run daily. Ends cancelled subscriptions at period end; for the rest opens a
    renewal order and marks the subscription past due until it is paid.

    Charging a saved card automatically needs a gateway with card tokens; with
    the sandbox the customer pays the renewal order like any other."""
    at = at or now()
    ended = renewed = 0
    due = db.scalars(select(Subscription).where(Subscription.status == "active", Subscription.current_period_end <= at))
    for subscription in list(due):
        if subscription.cancel_at_period_end:
            subscription.status = "expired"
            ended += 1
            continue
        pending = db.scalar(select(func.count()).select_from(Order).where(
            Order.target_id == subscription.id, Order.kind == "renewal", Order.status == "pending"))
        if not pending:
            plan = subscription.plan
            user = db.get(User, subscription.user_id)
            create_order(db, payments, user, kind="renewal", amount_minor=plan.price_minor, currency=plan.currency,
                         items=[{"key": plan.key, "title": plan.title["en"], "quantity": 1, "unit_minor": plan.price_minor}],
                         description=plan.title["en"], target_id=subscription.id)
        subscription.status = "past_due"
        renewed += 1
    db.flush()
    return {"expired": ended, "renewal_orders": renewed}
