"""Server-side release enforcement. Hiding a screen is never the control:
every router that belongs to a feature depends on `require_feature(key)`.

    router = APIRouter(dependencies=[Depends(require_feature("phase2.booking"))])
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.deps import get_optional_user
from app.core.errors import AppError
from app.database.session import get_db
from app.modules.auth.models import User
from app.modules.phase_management import service


def request_release(db: Session = Depends(get_db), _user: User | None = Depends(get_optional_user)) -> dict:
    """The active release this request is evaluated against. Resolving the
    (optional) user first means a refusal comes back in her saved language."""
    release, snapshot = service.current_snapshot(db)
    return {"release": release, "snapshot": snapshot, "preview": False}


def require_feature(key: str):
    def dependency(current: dict = Depends(request_release)) -> None:
        if key not in service.effective_keys(current["snapshot"]):
            # 404, not 403: a disabled feature should not reveal that it exists.
            raise AppError(404, "feature_not_available")

    return dependency


def enabled_features(current: dict = Depends(request_release)) -> set[str]:
    """Every feature key switched on for this request's release."""
    return service.effective_keys(current["snapshot"])
