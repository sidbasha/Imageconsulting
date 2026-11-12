import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.deps import get_current_user, get_optional_user, require_permission
from app.core.errors import AppError, pick_language
from app.database.session import get_db
from app.integrations.payments import PaymentProvider, SandboxPayments, get_payments
from app.modules.assessments.service import tr
from app.modules.auth.models import User
from app.modules.commerce import documents, service
from app.modules.commerce.models import Order, Plan, Product, RetailClick, RetailItem, Subscription
from app.modules.feature_flags.guard import enabled_features, require_feature
from app.modules.users.deps import eligible_user


def payments_provider() -> PaymentProvider:
    try:
        return get_payments()
    except RuntimeError as exc:
        raise AppError(503, "integration_not_configured", {"integration": "payments"}) from exc


PLAN_FEATURES = {"customer": "phase1.customer_subscriptions", "consultant": "phase2.consultant_subscriptions"}


def _product_visible(product: Product, on: set[str]) -> bool:
    if not product.is_active or product.feature_key not in on:
        return False
    # Paid items also need paid access (row 34); free resources do not.
    return product.is_free or "phase1.free_paid_access" in on or product.kind == "workspace_credits"


def product_out(product: Product, language: str, owned: bool | None = None) -> dict:
    return {
        "key": product.key, "kind": product.kind, "title": tr(product.title, language),
        "description": tr(product.description, language), "price_minor": product.price_minor,
        "currency": product.currency, "is_free": product.is_free, "requires_shipping": product.requires_shipping,
        "owned": owned,
    }


def plan_out(plan: Plan, language: str) -> dict:
    return {"key": plan.key, "audience": plan.audience, "title": tr(plan.title, language),
            "description": tr(plan.description, language), "price_minor": plan.price_minor,
            "currency": plan.currency, "interval": plan.interval}


router = APIRouter(tags=["shop"])


@router.get("/shop/products")
def products(
    request: Request, kind: str | None = None, on: set[str] = Depends(enabled_features),
    user: User | None = Depends(get_optional_user), db: Session = Depends(get_db),
) -> list[dict]:
    language = pick_language(request)
    query = select(Product).order_by(Product.sort_order)
    if kind:
        query = query.where(Product.kind == kind)
    out = []
    for product in db.scalars(query):
        if _product_visible(product, on):
            owned = None
            if user and product.kind in ("guide", "report"):
                owned = service.has_entitlement(db, user, product.key)
            out.append(product_out(product, language, owned))
    return out


@router.get("/shop/plans")
def plans(request: Request, audience: str = "customer", on: set[str] = Depends(enabled_features), db: Session = Depends(get_db)) -> list[dict]:
    if PLAN_FEATURES.get(audience) not in on:
        raise AppError(404, "feature_not_available")
    language = pick_language(request)
    return [plan_out(p, language) for p in db.scalars(
        select(Plan).where(Plan.audience == audience, Plan.is_active).order_by(Plan.sort_order))]


def _product(db: Session, key: str, on: set[str]) -> Product:
    product = db.execute(select(Product).where(Product.key == key)).scalar_one_or_none()
    if product is None or not _product_visible(product, on):
        raise AppError(404, "not_found")
    return product


class ShippingIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(pattern=r"^\+?[0-9 ]{7,20}$")
    line1: str = Field(min_length=1, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=1, max_length=80)
    country_code: str = Field(pattern="^[A-Za-z]{2}$")


class BuyIn(BaseModel):
    product_key: str
    quantity: int = Field(default=1, ge=1, le=20)
    shipping: ShippingIn | None = None


@router.post("/checkout/product", status_code=status.HTTP_201_CREATED)
def buy(
    body: BuyIn, request: Request, on: set[str] = Depends(enabled_features), user: User = Depends(eligible_user),
    db: Session = Depends(get_db), payments: PaymentProvider = Depends(payments_provider),
) -> dict:
    product = _product(db, body.product_key, on)
    if product.kind == "workspace_credits" and not user.has_permission("stylist.practice"):
        raise AppError(403, "permission_denied")
    shipping = body.shipping.model_dump() if body.shipping else None
    return service.buy_product(db, payments, user, product, body.quantity, shipping, pick_language(request))


class PlanIn(BaseModel):
    plan_key: str


@router.post("/checkout/plan", status_code=status.HTTP_201_CREATED)
def buy_plan(
    body: PlanIn, request: Request, on: set[str] = Depends(enabled_features), user: User = Depends(eligible_user),
    db: Session = Depends(get_db), payments: PaymentProvider = Depends(payments_provider),
) -> dict:
    plan = db.execute(select(Plan).where(Plan.key == body.plan_key, Plan.is_active)).scalar_one_or_none()
    if plan is None or PLAN_FEATURES[plan.audience] not in on:
        raise AppError(404, "not_found")
    if plan.audience == "consultant" and not user.has_permission("stylist.practice"):
        raise AppError(403, "permission_denied")
    return service.subscribe(db, payments, user, plan, pick_language(request))


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    status: str
    amount_minor: int
    currency: str
    items: list
    created_at: datetime
    paid_at: datetime | None
    fulfilment_status: str | None
    points_used: int


@router.get("/orders", response_model=list[OrderOut])
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())))


@router.get("/orders/{order_id}", response_model=OrderOut)
def my_order(order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise AppError(404, "not_found")
    return order


@router.post("/payments/webhook/{provider}", status_code=status.HTTP_204_NO_CONTENT, tags=["payments"])
async def webhook(provider: str, request: Request, db: Session = Depends(get_db), payments: PaymentProvider = Depends(payments_provider)) -> None:
    """Called by the payment gateway, not the app. Authenticated by the gateway's signature."""
    if provider != payments.name:
        raise AppError(404, "not_found")
    service.handle_webhook(db, payments, await request.body(), {k.lower(): v for k, v in request.headers.items()})


# Development only: pretend to be the gateway's payment page. Never mounted in production.
sandbox = APIRouter(prefix="/sandbox", tags=["sandbox"])


@sandbox.post("/pay/{reference}")
def sandbox_pay(reference: str, outcome: str = "paid", db: Session = Depends(get_db),
                payments: PaymentProvider = Depends(payments_provider)) -> dict:
    if get_settings().env == "production" or not isinstance(payments, SandboxPayments):
        raise AppError(404, "not_found")
    order = db.execute(select(Order).where(Order.provider_ref == reference)).scalar_one_or_none()
    if order is None:
        raise AppError(404, "not_found")
    body, headers = payments.webhook_body(reference, outcome, order.amount_minor, order.currency)
    order = service.handle_webhook(db, payments, body, headers)
    return {"order_id": order.id, "status": order.status}


# ---------------------------------------------------------------- entitlements, subscriptions

@router.get("/me/entitlements")
def my_entitlements(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    totals: dict[str, dict] = {}
    for e in service.active_entitlements(db, user):
        item = totals.setdefault(e.key, {"key": e.key, "quantity": 0, "expires_at": e.expires_at})
        item["quantity"] += e.quantity
        if e.expires_at is None or (item["expires_at"] and e.expires_at > item["expires_at"]):
            item["expires_at"] = e.expires_at
    return [v for v in totals.values() if v["quantity"] > 0]


@router.get("/me/subscriptions")
def my_subscriptions(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    language = pick_language(request)
    return [
        {"id": s.id, "status": s.status, "plan": plan_out(s.plan, language),
         "current_period_end": s.current_period_end, "cancel_at_period_end": s.cancel_at_period_end}
        for s in db.scalars(select(Subscription).where(Subscription.user_id == user.id).order_by(Subscription.created_at.desc()))
    ]


@router.post("/me/subscriptions/{subscription_id}/cancel")
def cancel(subscription_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    s = service.cancel_subscription(db, user, subscription_id)
    return {"id": s.id, "status": s.status, "cancel_at_period_end": s.cancel_at_period_end, "current_period_end": s.current_period_end}


# ---------------------------------------------------------------- library: guides and reports

library = APIRouter(prefix="/library", tags=["library"])


@library.get("")
def my_library(request: Request, on: set[str] = Depends(enabled_features), user: User = Depends(eligible_user), db: Session = Depends(get_db)) -> list[dict]:
    language = pick_language(request)
    return [
        product_out(p, language, True)
        for p in db.scalars(select(Product).where(Product.kind.in_(("guide", "report"))).order_by(Product.sort_order))
        if _product_visible(p, on) and (p.is_free or service.has_entitlement(db, user, p.key))
    ]


@library.post("/{product_key}/claim", status_code=status.HTTP_201_CREATED,
              dependencies=[Depends(require_feature("phase1.free_resources"))])
def claim_free(product_key: str, on: set[str] = Depends(enabled_features), user: User = Depends(eligible_user), db: Session = Depends(get_db)) -> dict:
    """Complimentary resources (row 39)."""
    product = _product(db, product_key, on)
    if not product.is_free:
        raise AppError(402, "payment_required")
    if not service.has_entitlement(db, user, product.key):
        service.grant(db, user.id, product.key, "free", product.id)
    return {"key": product.key, "owned": True}


@library.get("/{product_key}/download")
def download(product_key: str, request: Request, on: set[str] = Depends(enabled_features),
             user: User = Depends(eligible_user), db: Session = Depends(get_db)) -> Response:
    product = _product(db, product_key, on)
    if product.kind not in ("guide", "report"):
        raise AppError(404, "not_found")
    if not service.has_entitlement(db, user, product.key):
        raise AppError(402, "payment_required")
    filename, data = documents.render(db, user, product, pick_language(request))
    return Response(data, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})


# ---------------------------------------------------------------- retail links (row 36)

retail = APIRouter(prefix="/shop/retail", tags=["retail"], dependencies=[Depends(require_feature("phase1.retail_links"))])


@retail.get("")
def recommended_retail(request: Request, category: str = "outfits", user: User = Depends(eligible_user), db: Session = Depends(get_db)) -> dict:
    """Retailer items matched to the user's results by tags; best matches first."""
    language = pick_language(request)
    mine = {k: r["profile"].key for k, r in documents.user_results(db, user).items() if r["profile"]}
    scored = []
    for item in db.scalars(select(RetailItem).where(RetailItem.is_active, RetailItem.category == category)):
        score = sum(1 for dimension, values in item.tags.items() if mine.get(dimension) in values)
        if score or not item.tags:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1].retailer))
    return {
        "based_on": mine,
        "items": [{"id": i.id, "retailer": i.retailer, "title": tr(i.title, language), "image_url": i.image_url,
                   "price_text": i.price_text, "match": s} for s, i in scored],
    }


@retail.get("/{item_id}/go")
def go(item_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Counts the click, then sends the user to the retailer."""
    item = db.get(RetailItem, item_id)
    if item is None or not item.is_active:
        raise AppError(404, "not_found")
    item.clicks += 1
    db.add(RetailClick(item_id=item.id, user_id=user.id, created_at=datetime.now(UTC)))
    db.flush()
    return RedirectResponse(item.url, status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------------- admin (rows 55, 57)

admin = APIRouter(prefix="/admin", tags=["admin: commerce"])


class ProductPatch(BaseModel):
    title: dict | None = None
    description: dict | None = None
    price_minor: int | None = Field(default=None, ge=0)
    is_free: bool | None = None
    is_active: bool | None = None
    content_status: str | None = Field(default=None, pattern="^(draft|approved)$")


@admin.get("/products")
def admin_products(_: User = Depends(require_permission("content.manage")), db: Session = Depends(get_db)) -> list[dict]:
    return [{"key": p.key, "kind": p.kind, "title": p.title, "price_minor": p.price_minor, "is_free": p.is_free,
             "is_active": p.is_active, "content_status": p.content_status} for p in db.scalars(select(Product).order_by(Product.sort_order))]


@admin.patch("/products/{key}")
def patch_product(key: str, body: ProductPatch, user: User = Depends(require_permission("content.manage")), db: Session = Depends(get_db)) -> dict:
    product = db.execute(select(Product).where(Product.key == key)).scalar_one_or_none()
    if product is None:
        raise AppError(404, "not_found")
    changes = body.model_dump(exclude_none=True)
    if ({"price_minor", "is_free"} & changes.keys()) and not user.has_permission("pricing.manage"):
        raise AppError(403, "permission_denied")  # prices belong to finance (row 55)
    for k, v in changes.items():
        setattr(product, k, v)
    db.flush()
    return {"key": product.key, **changes}


class PlanPatch(BaseModel):
    price_minor: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    grants: list[str] | None = None
    title: dict | None = None


@admin.patch("/plans/{key}")
def patch_plan(key: str, body: PlanPatch, _: User = Depends(require_permission("pricing.manage")), db: Session = Depends(get_db)) -> dict:
    plan = db.execute(select(Plan).where(Plan.key == key)).scalar_one_or_none()
    if plan is None:
        raise AppError(404, "not_found")
    changes = body.model_dump(exclude_none=True)
    for k, v in changes.items():
        setattr(plan, k, v)
    db.flush()
    return {"key": plan.key, **changes}


@admin.get("/orders", response_model=list[OrderOut])
def admin_orders(status_filter: str | None = None, _: User = Depends(require_permission("orders.manage")), db: Session = Depends(get_db)):
    query = select(Order).order_by(Order.created_at.desc()).limit(200)
    if status_filter:
        query = query.where(Order.status == status_filter)
    return list(db.scalars(query))


class FulfilmentIn(BaseModel):
    fulfilment_status: str = Field(pattern="^(unfulfilled|shipped|delivered)$")


@admin.post("/orders/{order_id}/fulfilment", response_model=OrderOut)
def fulfil(order_id: uuid.UUID, body: FulfilmentIn, _: User = Depends(require_permission("orders.manage")), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None or order.shipping is None:
        raise AppError(404, "not_found")
    if order.status != "paid":
        raise AppError(409, "order_not_paid")
    order.fulfilment_status = body.fulfilment_status
    db.flush()
    return order


@admin.post("/orders/{order_id}/refund", response_model=OrderOut)
def admin_refund(order_id: uuid.UUID, _: User = Depends(require_permission("orders.manage")), db: Session = Depends(get_db),
                 payments: PaymentProvider = Depends(payments_provider)):
    order = db.get(Order, order_id)
    if order is None:
        raise AppError(404, "not_found")
    return service.refund(db, payments, order)


class RetailIn(BaseModel):
    retailer: str = Field(min_length=1, max_length=80)
    title: dict
    url: str = Field(pattern=r"^https://", max_length=500)
    image_url: str | None = Field(default=None, pattern=r"^https://", max_length=500)
    price_text: str | None = Field(default=None, max_length=40)
    category: str = Field(default="outfits", pattern="^(outfits|eyewear|hair|makeup|accessories)$")
    tags: dict[str, list[str]] = {}
    is_active: bool = True


@admin.post("/retail-items", status_code=status.HTTP_201_CREATED)
def add_retail(body: RetailIn, _: User = Depends(require_permission("content.manage")), db: Session = Depends(get_db)) -> dict:
    item = RetailItem(**body.model_dump())
    db.add(item)
    db.flush()
    return {"id": item.id}


@admin.put("/retail-items/{item_id}")
def put_retail(item_id: uuid.UUID, body: RetailIn, _: User = Depends(require_permission("content.manage")), db: Session = Depends(get_db)) -> dict:
    item = db.get(RetailItem, item_id)
    if item is None:
        raise AppError(404, "not_found")
    for k, v in body.model_dump().items():
        setattr(item, k, v)
    db.flush()
    return {"id": item.id}


@admin.get("/retail-items")
def list_retail(_: User = Depends(require_permission("content.manage")), db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": i.id, "retailer": i.retailer, "title": i.title, "url": i.url, "category": i.category,
             "tags": i.tags, "is_active": i.is_active, "clicks": i.clicks} for i in db.scalars(select(RetailItem))]
