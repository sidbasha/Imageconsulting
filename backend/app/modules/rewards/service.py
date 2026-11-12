"""Loyalty points (row 43) and redemption (row 44).

Rules and redemption options are DRAFT placeholders; the client sets real
values in the admin (row 59). Points are awarded only while loyalty points
are switched on in the active release.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.auth.models import User
from app.modules.commerce import service as commerce
from app.modules.commerce.models import Order
from app.modules.platform import service as platform
from app.modules.phase_management import service as releases
from app.modules.rewards.models import PointsEntry, RedemptionOption, RewardRule

RULES = [
    # event, points, max per day, once per ref, en, ar
    ("assessment_completed", 20, None, True, "Complete an assessment", "إكمال تقييم"),
    ("photo_analysis", 20, None, True, "Analyse a photo", "تحليل صورة"),
    ("purchase", 0, None, True, "Every purchase (points per AED, see settings)", "كل عملية شراء (نقاط لكل درهم)"),
    ("consultation_completed", 50, None, True, "Complete a consultation", "إكمال استشارة"),
    ("testimonial", 30, None, True, "Write a testimonial", "كتابة تقييم"),
    ("daily_visit", 2, 1, False, "Open the app (once a day)", "فتح التطبيق (مرة يومياً)"),
]
OPTIONS = [
    ("consultation_30", "Free 30-minute consultation", "استشارة مجانية لمدة ٣٠ دقيقة", 1000, "reward.consultation"),
]


def seed(db: Session) -> None:
    have = set(db.scalars(select(RewardRule.event)))
    for event, points, per_day, once, en, ar in RULES:
        if event not in have:
            db.add(RewardRule(event=event, points=points, max_per_day=per_day, once_per_ref=once, description={"en": en, "ar": ar}))
    keys = set(db.scalars(select(RedemptionOption.key)))
    for key, en, ar, cost, grants in OPTIONS:
        if key not in keys:
            db.add(RedemptionOption(key=key, title={"en": en, "ar": ar}, points_cost=cost, grants=grants))
    db.flush()


def balance(db: Session, user_id) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(PointsEntry.delta), 0)).where(PointsEntry.user_id == user_id)))


def award(db: Session, user_id, event: str, ref: str | None = None, points: int | None = None) -> int:
    """Adds points for an event if loyalty is switched on and the rule allows it. Returns points added."""
    if not releases.is_enabled(db, "phase1.loyalty_points"):
        return 0
    rule = db.execute(select(RewardRule).where(RewardRule.event == event, RewardRule.is_active)).scalar_one_or_none()
    if rule is None:
        return 0
    amount = rule.points if points is None else points
    if amount <= 0:
        return 0
    mine = select(func.count()).select_from(PointsEntry).where(PointsEntry.user_id == user_id, PointsEntry.event == event)
    if rule.once_per_ref and ref is not None and db.scalar(mine.where(PointsEntry.ref == ref)):
        return 0
    if rule.max_per_day is not None:
        since = datetime.now(UTC) - timedelta(days=1)
        if db.scalar(mine.where(PointsEntry.created_at >= since)) >= rule.max_per_day:
            return 0
    db.add(PointsEntry(user_id=user_id, delta=amount, event=event, ref=ref))
    db.flush()
    return amount


def _on_paid(db: Session, order: Order) -> None:
    if order.amount_minor > 0:
        per_aed = platform.get(db, "rewards.points_per_aed")
        award(db, order.user_id, "purchase", ref=str(order.id), points=int(order.amount_minor / 100 * per_aed))


commerce.AFTER_PAID.append(_on_paid)


def redeem(db: Session, user: User, option_key: str) -> dict:
    option = db.execute(select(RedemptionOption).where(RedemptionOption.key == option_key, RedemptionOption.is_active)).scalar_one_or_none()
    if option is None:
        raise AppError(404, "not_found")
    # Lock the user's ledger rows so two redemptions cannot spend the same points.
    db.execute(select(PointsEntry.id).where(PointsEntry.user_id == user.id).with_for_update())
    if balance(db, user.id) < option.points_cost:
        raise AppError(409, "not_enough_points", {"needed": option.points_cost})
    db.add(PointsEntry(user_id=user.id, delta=-option.points_cost, event="redeem", ref=option.key))
    commerce.grant(db, user.id, option.grants, "reward")
    db.flush()
    return {"redeemed": option.key, "balance": balance(db, user.id)}
