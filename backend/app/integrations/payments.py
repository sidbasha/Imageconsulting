"""Payment gateway behind one interface (rows 34-37, 40, 41).

Only the SANDBOX provider exists. The client has not chosen a gateway (UAE
options include Network International, Checkout.com, Telr, Stripe); each
needs a merchant account and must be built and certified against that
gateway's test environment. A real provider implements the same three
methods. Card data never touches this backend: the customer pays on the
gateway's page, and the gateway reports back through a signed webhook.

Sandbox: create_checkout returns a reference; the payment is completed by a
webhook signed with HMAC-SHA256 over the raw body (`X-Sandbox-Signature`),
exactly as a real gateway would call back. In development a helper route
does the signing; it is never mounted in production.
"""

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from typing import Protocol

from app.config.settings import get_settings


@dataclass
class Checkout:
    reference: str
    redirect_url: str


@dataclass
class WebhookEvent:
    reference: str
    status: str  # paid | failed
    amount_minor: int
    currency: str


class InvalidSignature(Exception):
    pass


class PaymentProvider(Protocol):
    name: str

    def create_checkout(self, *, order_id: str, amount_minor: int, currency: str, description: str) -> Checkout: ...
    def parse_webhook(self, body: bytes, headers: dict[str, str]) -> WebhookEvent: ...
    def refund(self, *, reference: str, amount_minor: int) -> str: ...


class SandboxPayments:
    name = "sandbox"
    SIGNATURE_HEADER = "x-sandbox-signature"

    def __init__(self, secret: str):
        self._secret = secret.encode()

    def sign(self, body: bytes) -> str:
        return hmac.new(self._secret, body, hashlib.sha256).hexdigest()

    def create_checkout(self, *, order_id: str, amount_minor: int, currency: str, description: str) -> Checkout:
        reference = f"sbx_{secrets.token_hex(10)}"
        return Checkout(reference=reference, redirect_url=f"/sandbox/pay/{reference}")

    def parse_webhook(self, body: bytes, headers: dict[str, str]) -> WebhookEvent:
        signature = headers.get(self.SIGNATURE_HEADER, "")
        if not hmac.compare_digest(self.sign(body), signature):
            raise InvalidSignature
        data = json.loads(body)
        return WebhookEvent(data["reference"], data["status"], int(data["amount_minor"]), data["currency"])

    def refund(self, *, reference: str, amount_minor: int) -> str:
        return f"sbx_refund_{secrets.token_hex(8)}"

    def webhook_body(self, reference: str, status: str, amount_minor: int, currency: str) -> tuple[bytes, dict]:
        """What the gateway would send. Used by tests and the development pay route."""
        body = json.dumps(
            {"reference": reference, "status": status, "amount_minor": amount_minor, "currency": currency}
        ).encode()
        return body, {self.SIGNATURE_HEADER: self.sign(body)}


def get_payments() -> PaymentProvider:
    settings = get_settings()
    if settings.env == "production":
        raise RuntimeError("no production payment provider is configured")
    return SandboxPayments(settings.jwt_secret + ":payments-sandbox")
