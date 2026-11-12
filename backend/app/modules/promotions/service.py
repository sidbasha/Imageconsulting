"""Promotions, brand advertising, geo targeting and vouchers (rows 42, 49-51, 60)."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.integrations.payments import PaymentProvider
from app.modules.auth.models import User
from app.modules.commerce import service as commerce
from app.modules.commerce.models import Order
from app.modules.marketplace.service import _distance_km
from app.modules.platform import service as platform
from app.modules.promotions.models import Campaign, Voucher, VoucherClaim

def now() -> datetime:
    return datetime.now(UTC)


def promoted_profile_ids(db: Session, enabled: set[str]) -> set[uuid.UUID]:
    t = now()
    return set(db.scalars(select(Campaign.profile_id).where(
        Campaign.advertiser_type == "stylist", Campaign.status == "active", Campaign.placement == "discovery_featured",
        Campaign.starts_at <= t, Campaign.ends_at > t)))


def buy_featured(db: Session, payments: PaymentProvider, stylist: User, profile_id: uuid.UUID, starts_at: datetime, days: int) -> dict:
    price = platform.get(db, "promotion.featured_price_per_day_minor") * days
    campaign = Campaign(advertiser_type="stylist", profile_id=profile_id, advertiser_name=stylist.full_name,
                        placement="discovery_featured", starts_at=starts_at, ends_at=starts_at + timedelta(days=days),
                        status="pending_payment", price_minor=price)
    db.add(campaign)
    db.flush()
    checkout = commerce.create_order(db, payments, stylist, kind="promotion", amount_minor=price, currency="AED",
                                     items=[{"key": "promotion.featured", "title": f"Featured placement, {days} days",
                                             "quantity": days, "unit_minor": price // days}],
                                     description="Featured placement", target_id=campaign.id)
    campaign.order_id = checkout["order_id"]
    db.flush()
    return {"campaign_id": campaign.id, "checkout": checkout}


def _on_paid(db: Session, order: Order) -> None:
    campaign = db.get(Campaign, order.target_id)
    if campaign.status == "pending_payment":
        campaign.status = "pending_review"  # an administrator approves placements (row 60)


def _on_refunded(db: Session, order: Order) -> None:
    db.get(Campaign, order.target_id).status = "cancelled"


commerce.ON_PAID["promotion"] = _on_paid
commerce.ON_REFUNDED["promotion"] = _on_refunded


def _in_area(item, lat, lng) -> bool:
    if item.radius_km is None or item.latitude is None:
        return True  # not targeted
    if lat is None or lng is None:
        return False  # targeted, and we do not know where the user is
    return _distance_km(lat, lng, item.latitude, item.longitude) <= item.radius_km


def live_campaigns(db: Session, enabled: set[str], placement: str, lat: float | None, lng: float | None) -> list[Campaign]:
    t = now()
    rows = db.scalars(select(Campaign).where(Campaign.status == "active", Campaign.placement == placement,
                                             Campaign.starts_at <= t, Campaign.ends_at > t, Campaign.advertiser_type == "brand"))
    geo = "phase3.geo_promotions" in enabled
    out = []
    for c in rows:
        if c.radius_km is not None and not geo:
            continue  # a targeted campaign waits until geo targeting is released
        if geo and not _in_area(c, lat, lng):
            continue
        c.impressions += 1
        out.append(c)
    db.flush()
    return out


def live_vouchers(db: Session, enabled: set[str], lat, lng) -> list[Voucher]:
    t = now()
    rows = db.scalars(select(Voucher).where(Voucher.is_active, Voucher.starts_at <= t, Voucher.ends_at > t))
    geo = "phase3.geo_promotions" in enabled
    return [v for v in rows if (v.max_claims is None or v.claimed < v.max_claims)
            and (v.radius_km is None or (geo and _in_area(v, lat, lng)))]


def claim(db: Session, user: User, voucher_id: uuid.UUID) -> Voucher:
    voucher = db.execute(select(Voucher).where(Voucher.id == voucher_id).with_for_update()).scalar_one_or_none()
    t = now()
    if voucher is None or not voucher.is_active or not (voucher.starts_at <= t < voucher.ends_at):
        raise AppError(404, "not_found")
    if db.execute(select(VoucherClaim.id).where(VoucherClaim.voucher_id == voucher.id, VoucherClaim.user_id == user.id)).first():
        return voucher  # claiming twice just shows the code again
    if voucher.max_claims is not None and voucher.claimed >= voucher.max_claims:
        raise AppError(409, "voucher_exhausted")
    voucher.claimed += 1
    db.add(VoucherClaim(voucher_id=voucher.id, user_id=user.id))
    db.flush()
    return voucher
