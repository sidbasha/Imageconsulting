import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config.settings import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("typ") != "access":
            return None
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def new_refresh_token() -> tuple[str, str]:
    """Returns (token for the client, hash stored in the database)."""
    token = secrets.token_urlsafe(48)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


DOWNLOAD_MINUTES = 5


def create_download_token(user_id: uuid.UUID, resource: str, language: str) -> str:
    """A short-lived link token for opening one document in a browser, which
    cannot send the app's Authorization header. Typed so it is never accepted
    as an access token, and bound to one resource."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "typ": "download", "res": resource, "lang": language,
               "iat": now, "exp": now + timedelta(minutes=DOWNLOAD_MINUTES)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_download_token(token: str) -> tuple[uuid.UUID, str, str] | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("typ") != "download":
            return None
        return uuid.UUID(payload["sub"]), payload["res"], payload["lang"]
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
