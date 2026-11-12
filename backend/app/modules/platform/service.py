"""Policy settings and markets.

Every default below is a PLACEHOLDER for an open client decision; the
decision it waits on is named next to it. Admins change them through
/admin/settings without a deploy.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.platform.models import Country, PlatformSetting

DEFAULTS: dict[str, tuple[object, str]] = {
    # Row 63, launch audience
    "eligibility.min_age": (18, "Minimum age in years. Row 63: treatment of teenagers is undecided."),
    "eligibility.women_only": (True, "Only women may register as customers. Row 63, from the discovery call."),
    "eligibility.manual_review": (False, "Hold every new customer for manual approval (row 53)."),
    # Row 65, verification and privacy
    "identity.delete_documents_after_review": (True, "Delete uploaded ID images once reviewed. Row 65: retention undecided."),
    # Row 33, violations
    "moderation.warn_after": (1, "Violations before a written warning. Row 33: threshold to be confirmed."),
    "moderation.suspend_after": (3, "Violations before messaging is suspended. Row 33: threshold to be confirmed."),
    "moderation.suspend_days": (14, "Length of a messaging suspension in days."),
    "moderation.ban_after": (5, "Violations before the account is deactivated."),
    # Row 66, stylist ranking
    "ranking.weights": (
        {"rating": 1.0, "testimonials": 0.5, "promoted": 2.0, "distance": 1.0},
        "Weights for stylist ordering. Row 66: how testimonials, paid placement and location interact.",
    ),
    # Row 29, metering
    "workspace.credits_per_client": (1, "Workspace credits used when a consultant opens a new client."),
    # Rows 43-44, rewards
    "rewards.points_per_aed": (1, "Points earned per AED spent."),
    # Row 19, booking
    "booking.cancel_hours": (24, "Hours before the start when a customer may still cancel with a refund."),
    "booking.slot_minutes": (30, "Default consultation length (discussed 30-minute format)."),
}

COUNTRIES = [
    # code, en, ar, currency, launch market
    ("AE", "United Arab Emirates", "الإمارات العربية المتحدة", "AED", True),
    ("MY", "Malaysia", "ماليزيا", "MYR", False),
    ("SG", "Singapore", "سنغافورة", "SGD", False),
    ("AU", "Australia", "أستراليا", "AUD", False),
]


def seed(db: Session) -> None:
    existing = set(db.scalars(select(PlatformSetting.key)))
    for key, (value, description) in DEFAULTS.items():
        if key not in existing:
            db.add(PlatformSetting(key=key, value=value, description=description))
    codes = set(db.scalars(select(Country.code)))
    for order, (code, en, ar, currency, launch) in enumerate(COUNTRIES):
        if code not in codes:
            db.add(Country(code=code, name={"en": en, "ar": ar}, currency=currency,
                           is_launch_market=launch, is_enabled=launch, sort_order=order))
    db.flush()


def get(db: Session, key: str):
    row = db.execute(select(PlatformSetting).where(PlatformSetting.key == key)).scalar_one_or_none()
    if row is not None:
        return row.value
    if key in DEFAULTS:
        return DEFAULTS[key][0]
    raise KeyError(key)


def set_value(db: Session, key: str, value) -> PlatformSetting:
    if key not in DEFAULTS:
        raise AppError(404, "not_found")
    expected = type(DEFAULTS[key][0])
    if expected is float and isinstance(value, int):
        value = float(value)
    if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
        raise AppError(422, "invalid_setting", {"expected": expected.__name__})
    row = db.execute(select(PlatformSetting).where(PlatformSetting.key == key)).scalar_one_or_none()
    if row is None:
        row = PlatformSetting(key=key, value=value, description=DEFAULTS[key][1])
        db.add(row)
    row.value = value
    db.flush()
    return row


def available_countries(db: Session, enabled_features: set[str]) -> list[Country]:
    """UAE only at launch (row 3). Other enabled markets appear once
    international expansion (row 52) is released."""
    rows = list(db.scalars(select(Country).where(Country.is_enabled).order_by(Country.sort_order)))
    if "phase3.international_expansion" in enabled_features:
        return rows
    return [c for c in rows if c.is_launch_market]
