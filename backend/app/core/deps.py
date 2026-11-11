from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.modules.auth.models import User

_bearer = HTTPBearer(auto_error=False)


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.is_active or user.deleted_at is not None:
        raise AppError(401, "invalid_token")
    # Signed-in users get responses in the language saved on their profile.
    request.state.language = user.preferred_language
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise AppError(401, "not_authenticated")
    return user


def require_permission(key: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(key):
            raise AppError(403, "permission_denied")
        return user

    return dependency
