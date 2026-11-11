"""Server-side release enforcement. Hiding a screen is never the control:
every router that belongs to a feature depends on `require_feature(key)`.

    router = APIRouter(dependencies=[Depends(require_feature("phase2.booking"))])
"""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_optional_user
from app.core.errors import AppError
from app.database.session import get_db
from app.modules.auth.models import User
from app.modules.phase_management import service

PREVIEW_HEADER = "X-Release-Preview"


def request_release(
    request: Request, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)
) -> dict:
    """The release this request is evaluated against. Only a Super Admin can
    preview a stored release; from anyone else the header is ignored."""
    preview_id = request.headers.get(PREVIEW_HEADER)
    if preview_id and user is not None and user.has_permission("release.manage"):
        release, snapshot = service.preview_snapshot(db, preview_id)
        return {"release": release, "snapshot": snapshot, "preview": True}
    release, snapshot = service.current_snapshot(db)
    return {"release": release, "snapshot": snapshot, "preview": False}


def require_feature(key: str):
    def dependency(current: dict = Depends(request_release)) -> None:
        if key not in service.effective_keys(current["snapshot"]):
            # 404, not 403: a disabled feature should not reveal that it exists.
            raise AppError(404, "feature_not_available")

    return dependency
