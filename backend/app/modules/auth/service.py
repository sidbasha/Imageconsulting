from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core import security
from app.core.errors import AppError
from app.modules.auth.models import RefreshToken, Role, User
from app.modules.auth.schemas import TokenOut


def _role(db: Session, key: str) -> Role:
    return db.execute(select(Role).where(Role.key == key)).scalar_one()


def create_user(
    db: Session, *, email: str, password: str, full_name: str, language: str = "en", role_key: str = "customer"
) -> User:
    email = email.strip().lower()
    if db.execute(select(User.id).where(User.email == email)).first():
        raise AppError(409, "email_exists")
    user = User(
        email=email,
        password_hash=security.hash_password(password),
        full_name=full_name.strip(),
        preferred_language=language,
        role=_role(db, role_key),
    )
    db.add(user)
    db.flush()
    return user


def issue_tokens(db: Session, user: User) -> TokenOut:
    token, token_hash = security.new_refresh_token()
    expires = datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days)
    db.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires))
    db.flush()
    return TokenOut(access_token=security.create_access_token(user.id), refresh_token=token)


def login(db: Session, email: str, password: str) -> TokenOut:
    user = db.execute(select(User).where(User.email == email.strip().lower())).scalar_one_or_none()
    if user is None or not security.verify_password(password, user.password_hash):
        raise AppError(401, "invalid_credentials")
    if not user.is_active or user.deleted_at is not None:
        raise AppError(403, "account_inactive")
    return issue_tokens(db, user)


def _live_refresh_token(db: Session, token: str) -> RefreshToken | None:
    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == security.hash_refresh_token(token)).with_for_update()
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None or row.expires_at <= datetime.now(UTC):
        return None
    return row


def refresh(db: Session, token: str) -> TokenOut:
    """Rotation: each refresh token works once."""
    row = _live_refresh_token(db, token)
    if row is None:
        raise AppError(401, "invalid_token")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise AppError(401, "invalid_token")
    row.revoked_at = datetime.now(UTC)
    return issue_tokens(db, user)


def logout(db: Session, token: str) -> None:
    row = _live_refresh_token(db, token)
    if row is not None:
        row.revoked_at = datetime.now(UTC)
