from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.modules.auth.models import User
from app.modules.feature_flags.guard import enabled_features
from app.modules.users import service


def eligible_user(
    user: User = Depends(get_current_user), db: Session = Depends(get_db), on: set[str] = Depends(enabled_features)
) -> User:
    """The signed-in user, refused (403 not_eligible) if she is a customer who
    does not meet the eligibility and market rules switched on in this release."""
    service.require_eligible(db, user, on)
    return user


def verified_user(
    user: User = Depends(eligible_user), db: Session = Depends(get_db), on: set[str] = Depends(enabled_features)
) -> User:
    """As eligible_user, and with a verified identity when identity verification is switched on."""
    service.require_verified_identity(db, user, on)
    return user
