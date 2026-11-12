"""UAE Pass sign-in for identity verification (Feature List row 1).

Only the SANDBOX provider exists. It stands in for UAE Pass in development and
tests so the whole verification flow can run: the "authorisation code" is a
signed token that carries the claims a real UAE Pass profile would return.

The real provider is NOT written. It needs the client's UAE Pass onboarding
(client id and secret, redirect URI registered with TDRA, staging access) and
must be built and tested against the UAE Pass staging environment. It will
implement the same two methods: authorize_url() and exchange().
"""

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.config.settings import get_settings


@dataclass
class UaePassProfile:
    subject: str  # UAE Pass user id; stored, so one UAE Pass account verifies one user
    full_name: str
    gender: str | None  # female | male
    date_of_birth: date | None
    nationality: str | None


class UaePassProvider(Protocol):
    name: str

    def authorize_url(self, state: str) -> str: ...
    def exchange(self, code: str) -> UaePassProfile: ...


class InvalidCode(Exception):
    pass


class SandboxUaePass:
    name = "sandbox"

    def __init__(self, secret: str):
        self._secret = secret.encode()

    def authorize_url(self, state: str) -> str:
        return f"/sandbox/uae-pass/authorize?state={state}"

    def _sign(self, body: bytes) -> str:
        return hmac.new(self._secret, body, hashlib.sha256).hexdigest()

    def issue_code(self, **claims) -> str:
        """Test and development helper: what UAE Pass would redirect back with."""
        body = base64.urlsafe_b64encode(json.dumps(claims, default=str).encode())
        return f"{body.decode()}.{self._sign(body)}"

    def exchange(self, code: str) -> UaePassProfile:
        try:
            body, signature = code.rsplit(".", 1)
        except ValueError as exc:
            raise InvalidCode from exc
        if not hmac.compare_digest(self._sign(body.encode()), signature):
            raise InvalidCode
        claims = json.loads(base64.urlsafe_b64decode(body))
        dob = claims.get("date_of_birth")
        return UaePassProfile(
            subject=claims["subject"],
            full_name=claims.get("full_name", ""),
            gender=claims.get("gender"),
            date_of_birth=date.fromisoformat(dob) if dob else None,
            nationality=claims.get("nationality"),
        )


def get_uae_pass() -> UaePassProvider:
    settings = get_settings()
    if settings.env == "production":
        # Refuse to pretend: production must not accept sandbox codes.
        raise RuntimeError("UAE Pass production provider is not implemented")
    return SandboxUaePass(settings.jwt_secret + ":uae-pass-sandbox")
