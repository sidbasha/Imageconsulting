from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.core.errors import AppError, pick_language
from app.database.session import get_db
from app.modules.assessments.service import tr
from app.modules.auth.models import User
from app.modules.feature_flags.guard import require_feature
from app.modules.rewards import service
from app.modules.rewards.models import PointsEntry, RedemptionOption, RewardRule
from app.modules.users.deps import eligible_user

router = APIRouter(prefix="/rewards", tags=["rewards"], dependencies=[Depends(require_feature("phase1.loyalty_points"))])


@router.get("")
def my_points(request: Request, user: User = Depends(eligible_user), db: Session = Depends(get_db)) -> dict:
    language = pick_language(request)
    history = db.scalars(select(PointsEntry).where(PointsEntry.user_id == user.id).order_by(PointsEntry.created_at.desc()).limit(50))
    return {
        "balance": service.balance(db, user.id),
        "how_to_earn": [{"event": r.event, "points": r.points, "description": tr(r.description, language)}
                        for r in db.scalars(select(RewardRule).where(RewardRule.is_active)) if r.points > 0 or r.event == "purchase"],
        "history": [{"delta": e.delta, "event": e.event, "created_at": e.created_at} for e in history],
    }


@router.post("/daily-visit")
def daily_visit(user: User = Depends(eligible_user), db: Session = Depends(get_db)) -> dict:
    return {"awarded": service.award(db, user.id, "daily_visit"), "balance": service.balance(db, user.id)}


redeem = APIRouter(prefix="/rewards/redeem", tags=["rewards"], dependencies=[Depends(require_feature("phase2.reward_redemption"))])


@redeem.get("")
def options(request: Request, _: User = Depends(eligible_user), db: Session = Depends(get_db)) -> list[dict]:
    language = pick_language(request)
    return [{"key": o.key, "title": tr(o.title, language), "points_cost": o.points_cost}
            for o in db.scalars(select(RedemptionOption).where(RedemptionOption.is_active))]


@redeem.post("/{option_key}", status_code=status.HTTP_201_CREATED)
def redeem_option(option_key: str, user: User = Depends(eligible_user), db: Session = Depends(get_db)) -> dict:
    return service.redeem(db, user, option_key)


admin = APIRouter(prefix="/admin/rewards", tags=["admin: rewards"])


class RulePatch(BaseModel):
    points: int | None = Field(default=None, ge=0, le=100000)
    max_per_day: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


@admin.get("/rules")
def rules(_: User = Depends(require_permission("rewards.manage")), db: Session = Depends(get_db)) -> list[dict]:
    return [{"event": r.event, "points": r.points, "max_per_day": r.max_per_day, "is_active": r.is_active}
            for r in db.scalars(select(RewardRule))]


@admin.patch("/rules/{event}")
def patch_rule(event: str, body: RulePatch, _: User = Depends(require_permission("rewards.manage")), db: Session = Depends(get_db)) -> dict:
    rule = db.execute(select(RewardRule).where(RewardRule.event == event)).scalar_one_or_none()
    if rule is None:
        raise AppError(404, "not_found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(rule, k, v)
    db.flush()
    return {"event": rule.event, "points": rule.points, "is_active": rule.is_active}


@admin.get("/options")
def options_admin(_: User = Depends(require_permission("rewards.manage")), db: Session = Depends(get_db)) -> list[dict]:
    return [{"key": o.key, "title": o.title, "points_cost": o.points_cost, "is_active": o.is_active} for o in db.scalars(select(RedemptionOption))]


class OptionPatch(BaseModel):
    points_cost: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


@admin.patch("/options/{key}")
def patch_option(key: str, body: OptionPatch, _: User = Depends(require_permission("rewards.manage")), db: Session = Depends(get_db)) -> dict:
    option = db.execute(select(RedemptionOption).where(RedemptionOption.key == key)).scalar_one_or_none()
    if option is None:
        raise AppError(404, "not_found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(option, k, v)
    db.flush()
    return {"key": option.key, "points_cost": option.points_cost, "is_active": option.is_active}


class AdjustIn(BaseModel):
    delta: int
    reason: str = Field(min_length=3, max_length=80)


@admin.post("/users/{user_id}/adjust")
def adjust(user_id: str, body: AdjustIn, _: User = Depends(require_permission("rewards.manage")), db: Session = Depends(get_db)) -> dict:
    db.add(PointsEntry(user_id=user_id, delta=body.delta, event="adjustment", ref=body.reason))
    db.flush()
    return {"balance": service.balance(db, user_id)}
