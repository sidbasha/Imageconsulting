import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.core.errors import AppError, pick_language
from app.database.session import get_db
from app.integrations.payments import PaymentProvider
from app.modules.assessments.service import tr
from app.modules.auth.models import User
from app.modules.commerce.router import payments_provider
from app.modules.feature_flags.guard import enabled_features, require_feature
from app.modules.marketplace import service as marketplace
from app.modules.promotions import service
from app.modules.promotions.models import Campaign, Voucher, VoucherClaim
from app.modules.users.deps import eligible_user


def campaign_out(c: Campaign, language: str) -> dict:
    return {"id": c.id, "advertiser": c.advertiser_name, "placement": c.placement, "title": tr(c.title, language),
            "body": tr(c.body, language), "image_url": c.image_url, "has_link": bool(c.target_url)}


# ---------------------------------------------------------------- stylist paid promotion (42)

featured = APIRouter(prefix="/stylist/promotions", tags=["stylist promotion"], dependencies=[Depends(require_feature("phase2.paid_promotion"))])


class FeaturedIn(BaseModel):
    starts_at: datetime
    days: int = Field(ge=1, le=90)


@featured.post("", status_code=status.HTTP_201_CREATED)
def buy(body: FeaturedIn, user: User = Depends(get_current_user), db: Session = Depends(get_db),
        on: set[str] = Depends(enabled_features), payments: PaymentProvider = Depends(payments_provider)) -> dict:
    profile = marketplace.require_practising(db, user, on)
    if body.starts_at.tzinfo is None:
        raise AppError(422, "timezone_required")
    return service.buy_featured(db, payments, user, profile.id, body.starts_at, body.days)


@featured.get("")
def mine(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    profile = marketplace.require_profile(db, user)
    return [{"id": c.id, "status": c.status, "starts_at": c.starts_at, "ends_at": c.ends_at, "impressions": c.impressions}
            for c in db.scalars(select(Campaign).where(Campaign.profile_id == profile.id).order_by(Campaign.starts_at.desc()))]


# ---------------------------------------------------------------- brand advertising and geo (49, 50)

ads = APIRouter(prefix="/promotions", tags=["promotions"], dependencies=[Depends(require_feature("phase3.brand_advertising"))])


@ads.get("")
def placements(request: Request, placement: str = Query(default="home_banner", pattern="^(home_banner|offers)$"),
               lat: float | None = Query(default=None, ge=-90, le=90), lng: float | None = Query(default=None, ge=-180, le=180),
               on: set[str] = Depends(enabled_features), _: User = Depends(eligible_user), db: Session = Depends(get_db)) -> list[dict]:
    language = pick_language(request)
    return [campaign_out(c, language) for c in service.live_campaigns(db, on, placement, lat, lng)]


@ads.get("/{campaign_id}/go")
def go(campaign_id: uuid.UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if c is None or c.status != "active" or not c.target_url:
        raise AppError(404, "not_found")
    c.clicks += 1
    db.flush()
    return RedirectResponse(c.target_url, status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------------- vouchers (51)

vouchers = APIRouter(prefix="/vouchers", tags=["vouchers"], dependencies=[Depends(require_feature("phase3.vouchers"))])


def voucher_out(v: Voucher, language: str, code: str | None = None) -> dict:
    return {"id": v.id, "partner": v.partner_name, "title": tr(v.title, language), "terms": tr(v.terms, language),
            "ends_at": v.ends_at, "remaining": None if v.max_claims is None else v.max_claims - v.claimed, "code": code}


@vouchers.get("")
def available(request: Request, lat: float | None = None, lng: float | None = None, on: set[str] = Depends(enabled_features),
              _: User = Depends(eligible_user), db: Session = Depends(get_db)) -> list[dict]:
    language = pick_language(request)
    return [voucher_out(v, language) for v in service.live_vouchers(db, on, lat, lng)]


@vouchers.post("/{voucher_id}/claim", status_code=status.HTTP_201_CREATED)
def claim(voucher_id: uuid.UUID, request: Request, user: User = Depends(eligible_user), db: Session = Depends(get_db)) -> dict:
    v = service.claim(db, user, voucher_id)
    return voucher_out(v, pick_language(request), code=v.code)


@vouchers.get("/mine")
def my_vouchers(request: Request, user: User = Depends(eligible_user), db: Session = Depends(get_db)) -> list[dict]:
    language = pick_language(request)
    rows = db.execute(select(Voucher).join(VoucherClaim, VoucherClaim.voucher_id == Voucher.id).where(VoucherClaim.user_id == user.id)).scalars()
    return [voucher_out(v, language, code=v.code) for v in rows]


# ---------------------------------------------------------------- admin (60)

admin = APIRouter(prefix="/admin/promotions", tags=["admin: promotions"])


class CampaignIn(BaseModel):
    advertiser_name: str = Field(min_length=1, max_length=120)
    placement: str = Field(pattern="^(home_banner|offers)$")
    title: dict[str, str]
    body: dict[str, str] = {}
    image_url: str | None = Field(default=None, pattern=r"^https://")
    target_url: str | None = Field(default=None, pattern=r"^https://")
    starts_at: datetime
    ends_at: datetime
    price_minor: int = Field(default=0, ge=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float | None = Field(default=None, gt=0, le=500)


@admin.post("/campaigns", status_code=status.HTTP_201_CREATED)
def create_campaign(body: CampaignIn, _: User = Depends(require_permission("promotions.manage")), db: Session = Depends(get_db)) -> dict:
    """Brand campaigns are sold and invoiced by the client's team, then entered here."""
    if body.ends_at <= body.starts_at:
        raise AppError(422, "invalid_dates")
    if (body.radius_km is None) != (body.latitude is None) or (body.latitude is None) != (body.longitude is None):
        raise AppError(422, "invalid_geo_target")
    c = Campaign(advertiser_type="brand", status="active", **body.model_dump())
    db.add(c)
    db.flush()
    return {"id": c.id, "status": c.status}


@admin.get("/campaigns")
def campaigns(status_filter: str | None = None, _: User = Depends(require_permission("promotions.manage")), db: Session = Depends(get_db)) -> list[dict]:
    q = select(Campaign).order_by(Campaign.starts_at.desc())
    if status_filter:
        q = q.where(Campaign.status == status_filter)
    return [{"id": c.id, "advertiser_type": c.advertiser_type, "advertiser": c.advertiser_name, "placement": c.placement,
             "status": c.status, "starts_at": c.starts_at, "ends_at": c.ends_at, "impressions": c.impressions,
             "clicks": c.clicks, "price_minor": c.price_minor, "radius_km": c.radius_km} for c in db.scalars(q)]


class CampaignDecision(BaseModel):
    status: str = Field(pattern="^(active|rejected|cancelled)$")


@admin.post("/campaigns/{campaign_id}/status")
def set_status(campaign_id: uuid.UUID, body: CampaignDecision, _: User = Depends(require_permission("promotions.manage")), db: Session = Depends(get_db)) -> dict:
    c = db.get(Campaign, campaign_id)
    if c is None:
        raise AppError(404, "not_found")
    if c.status == "pending_payment" and body.status == "active":
        raise AppError(409, "order_not_paid")
    c.status = body.status
    db.flush()
    return {"id": c.id, "status": c.status}


class VoucherIn(BaseModel):
    partner_name: str = Field(min_length=1, max_length=120)
    title: dict[str, str]
    terms: dict[str, str] = {}
    code: str = Field(min_length=3, max_length=40)
    starts_at: datetime
    ends_at: datetime
    max_claims: int | None = Field(default=None, ge=1)
    latitude: float | None = None
    longitude: float | None = None
    radius_km: float | None = Field(default=None, gt=0, le=500)


@admin.post("/vouchers", status_code=status.HTTP_201_CREATED)
def create_voucher(body: VoucherIn, _: User = Depends(require_permission("promotions.manage")), db: Session = Depends(get_db)) -> dict:
    if body.ends_at <= body.starts_at:
        raise AppError(422, "invalid_dates")
    v = Voucher(**body.model_dump())
    db.add(v)
    db.flush()
    return {"id": v.id}


@admin.get("/vouchers")
def list_vouchers(_: User = Depends(require_permission("promotions.manage")), db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": v.id, "partner": v.partner_name, "title": v.title, "claimed": v.claimed, "max_claims": v.max_claims,
             "starts_at": v.starts_at, "ends_at": v.ends_at, "is_active": v.is_active} for v in db.scalars(select(Voucher))]
