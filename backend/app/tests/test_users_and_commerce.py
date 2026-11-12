from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.integrations.payments import SandboxPayments, get_payments
from app.integrations.uae_pass import get_uae_pass
from app.modules.commerce import service as commerce
from app.modules.commerce.models import Entitlement, Order, RetailItem, Subscription
from app.modules.users.models import CustomerProfile
from app.tests.conftest import ELIGIBLE, login
from app.tests.test_assessments import STYLE_ROMANTIC, answer

API = "/api/v1"


def register(client, email, **extra):
    body = {"email": email, "password": "a-long-enough-password", "full_name": "Test", **extra}
    response = client.post(f"{API}/auth/register", json=body)
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def pay(client, order_id_or_checkout, outcome="paid"):
    reference = order_id_or_checkout["payment_url"].rsplit("/", 1)[1]
    return client.post(f"{API}/sandbox/pay/{reference}", params={"outcome": outcome})


# ---------- eligibility (rows 2, 3, 52) ----------

def test_customer_features_need_a_complete_eligible_profile(client):
    headers = register(client, "new@example.com")
    blocked = client.get(f"{API}/assessments", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["detail"] == {"status": "incomplete", "reasons": ["profile_incomplete"]}
    profile = client.put(f"{API}/users/me/profile", json=ELIGIBLE, headers=headers).json()
    assert profile["eligibility_status"] == "eligible"
    assert client.get(f"{API}/assessments", headers=headers).status_code == 200


@pytest.mark.parametrize("facts, reason", [
    ({**ELIGIBLE, "gender": "male"}, "women_only"),
    ({**ELIGIBLE, "date_of_birth": (date.today() - timedelta(days=365 * 15)).isoformat()}, "under_minimum_age"),
    ({**ELIGIBLE, "country_code": "MY"}, "country_not_available"),
])
def test_ineligible_users_are_told_why(client, facts, reason):
    headers = register(client, "x@example.com", **facts)
    profile = client.get(f"{API}/users/me/profile", headers=headers).json()
    assert profile["eligibility_status"] == "ineligible" and profile["eligibility_reasons"] == [reason]
    assert client.get(f"{API}/assessments", headers=headers).status_code == 403


def test_policy_settings_change_the_rules_without_a_deploy(client, owner):
    headers = register(client, "teen@example.com", **{**ELIGIBLE, "date_of_birth": (date.today() - timedelta(days=365 * 16 + 5)).isoformat()})
    assert client.get(f"{API}/assessments", headers=headers).status_code == 403
    assert client.put(f"{API}/admin/settings/eligibility.min_age", json={"value": 16}, headers=owner).status_code == 200
    assert client.get(f"{API}/assessments", headers=headers).status_code == 200
    bad = client.put(f"{API}/admin/settings/eligibility.min_age", json={"value": "sixteen"}, headers=owner)
    assert bad.status_code == 422


def test_other_markets_open_only_with_international_expansion(client, owner, release):
    headers = register(client, "sg@example.com", **{**ELIGIBLE, "country_code": "SG"})
    assert [c["code"] for c in client.get(f"{API}/countries").json()] == ["AE"]
    client.put(f"{API}/admin/countries/SG", json={"is_enabled": True}, headers=owner)
    assert [c["code"] for c in client.get(f"{API}/countries").json()] == ["AE"]  # still Phase 1 only
    assert release(phases={"phase2": True, "phase3": True}).status_code == 201
    assert [c["code"] for c in client.get(f"{API}/countries").json()] == ["AE", "SG"]
    assert client.get(f"{API}/assessments", headers=headers).status_code == 200
    assert client.put(f"{API}/admin/countries/AE", json={"is_enabled": False}, headers=owner).status_code == 409


def test_manual_review_holds_new_customers_until_approved(client, owner):
    client.put(f"{API}/admin/settings/eligibility.manual_review", json={"value": True}, headers=owner)
    headers = register(client, "held@example.com", **ELIGIBLE)
    assert client.get(f"{API}/users/me/profile", headers=headers).json()["eligibility_status"] == "pending_review"
    queue = client.get(f"{API}/admin/eligibility", headers=owner).json()
    assert [q["email"] for q in queue] == ["held@example.com"]
    client.post(f"{API}/admin/eligibility/{queue[0]['user_id']}", json={"approve": True}, headers=owner)
    assert client.get(f"{API}/assessments", headers=headers).status_code == 200


def test_client_admin_reviews_users_but_cannot_release(client):
    admin = login(client, "client-admin@example.com")
    assert client.get(f"{API}/admin/eligibility", headers=admin).status_code == 200
    assert client.get(f"{API}/admin/phase-management/state", headers=admin).status_code == 403
    assert client.get(f"{API}/admin/eligibility", headers=login(client, "customer@example.com")).status_code == 403


# ---------- identity (row 1) ----------

def test_uae_pass_verifies_and_replaces_self_declared_facts(client):
    headers = register(client, "pass@example.com", **{**ELIGIBLE, "date_of_birth": "1991-01-01"})
    start = client.get(f"{API}/identity/uae-pass/start", headers=headers).json()
    assert start["provider"] == "sandbox"
    code = get_uae_pass().issue_code(subject="uaepass-123", full_name="Test", gender="female", date_of_birth="1988-02-03")
    done = client.post(f"{API}/identity/uae-pass/complete", json={"code": code}, headers=headers)
    assert done.status_code == 201 and done.json()["status"] == "verified"
    profile = client.get(f"{API}/users/me/profile", headers=headers).json()
    assert profile["identity_status"] == "verified" and profile["date_of_birth"] == "1988-02-03"
    # Verified facts are locked.
    locked = client.put(f"{API}/users/me/profile", json={"date_of_birth": "2000-01-01"}, headers=headers)
    assert locked.status_code == 409
    # The same UAE Pass account cannot verify a second user.
    other = register(client, "other@example.com", **ELIGIBLE)
    assert client.post(f"{API}/identity/uae-pass/complete", json={"code": code}, headers=other).status_code == 409
    forged = code[:-4] + "0000"
    assert client.post(f"{API}/identity/uae-pass/complete", json={"code": forged}, headers=other).status_code == 422


def test_id_document_is_reviewed_and_then_deleted(client, owner, tmp_path):
    from app.integrations.storage import LocalStorage, get_storage

    storage = LocalStorage(str(tmp_path))
    client.app.dependency_overrides[get_storage] = lambda: storage
    headers = register(client, "doc@example.com", **ELIGIBLE)
    uploaded = client.post(f"{API}/identity/documents", files={"front": ("id.jpg", b"\xff\xd8 front", "image/jpeg")}, headers=headers)
    assert uploaded.status_code == 201 and uploaded.json()["status"] == "pending"
    assert len(list(tmp_path.rglob("*.jpg"))) == 1
    pending = client.get(f"{API}/admin/identity/pending", headers=owner).json()
    verification = pending[0]["id"]
    assert client.get(f"{API}/admin/identity/{verification}/documents/0", headers=owner).content == b"\xff\xd8 front"
    missing_facts = client.post(f"{API}/admin/identity/{verification}/review", json={"approve": True}, headers=owner)
    assert missing_facts.status_code == 422
    review = {"approve": True, "date_of_birth": "1990-05-01", "gender": "female"}
    assert client.post(f"{API}/admin/identity/{verification}/review", json=review, headers=owner).json()["status"] == "verified"
    assert list(tmp_path.rglob("*.jpg")) == []  # deleted after review (row 65 default)
    assert client.get(f"{API}/users/me/profile", headers=headers).json()["identity_status"] == "verified"


# ---------- commerce (rows 34-39) ----------

def test_free_palettes_are_claimed_and_downloaded_as_pdf_in_both_languages(client, customer):
    shop = client.get(f"{API}/shop/products", params={"kind": "guide"}, headers=customer).json()
    free = [p for p in shop if p["is_free"]]
    assert len(free) == 4 and free[0]["price_minor"] == 0
    key = "guide.palette.spring"
    assert client.get(f"{API}/library/{key}/download", headers=customer).status_code == 402
    assert client.post(f"{API}/library/{key}/claim", headers=customer).status_code == 201
    arabic = client.get(f"{API}/library/{key}/download", headers=customer)
    assert arabic.status_code == 200 and arabic.content.startswith(b"%PDF") and arabic.headers["content-type"] == "application/pdf"
    english = client.get(f"{API}/library/{key}/download", headers={**customer, "Accept-Language": "en"})
    assert english.content.startswith(b"%PDF") and english.content != arabic.content
    paid = client.post(f"{API}/library/guide.body.pear/claim", headers=customer)
    assert paid.status_code == 402


def test_buying_a_guide_through_the_sandbox_gateway(client, customer, db):
    checkout = client.post(f"{API}/checkout/product", json={"product_key": "guide.body.pear"}, headers=customer)
    assert checkout.status_code == 201
    body = checkout.json()
    assert body["status"] == "pending" and body["amount_minor"] == 2900 and body["currency"] == "AED"
    assert client.get(f"{API}/library/guide.body.pear/download", headers=customer).status_code == 402
    assert pay(client, body).json()["status"] == "paid"
    assert pay(client, body).json()["status"] == "paid"  # a repeated webhook is harmless
    assert db.scalar(select(Entitlement).where(Entitlement.key == "guide.body.pear")) is not None
    assert len(db.scalars(select(Entitlement).where(Entitlement.key == "guide.body.pear")).all()) == 1
    assert client.get(f"{API}/library/guide.body.pear/download", headers=customer).status_code == 200
    again = client.post(f"{API}/checkout/product", json={"product_key": "guide.body.pear"}, headers=customer)
    assert again.status_code == 409


def test_webhook_rejects_bad_signatures_and_wrong_amounts(client, customer):
    body = client.post(f"{API}/checkout/product", json={"product_key": "guide.body.pear"}, headers=customer).json()
    reference = body["payment_url"].rsplit("/", 1)[1]
    payments: SandboxPayments = get_payments()
    raw, headers = payments.webhook_body(reference, "paid", 2900, "AED")
    assert client.post(f"{API}/payments/webhook/sandbox", content=raw, headers={"x-sandbox-signature": "0" * 64}).status_code == 400
    cheap, cheap_headers = payments.webhook_body(reference, "paid", 100, "AED")
    assert client.post(f"{API}/payments/webhook/sandbox", content=cheap, headers=cheap_headers).status_code == 400
    assert client.post(f"{API}/payments/webhook/sandbox", content=raw, headers=headers).status_code == 204
    assert client.get(f"{API}/orders/{body['order_id']}", headers=customer).json()["status"] == "paid"


def test_failed_payment_grants_nothing(client, customer):
    body = client.post(f"{API}/checkout/product", json={"product_key": "report.full_assessment"}, headers=customer).json()
    assert pay(client, body, "failed").json()["status"] == "failed"
    assert client.get(f"{API}/library/report.full_assessment/download", headers=customer).status_code == 402


def test_full_report_uses_the_users_results(client, customer):
    body = client.post(f"{API}/checkout/product", json={"product_key": "report.full_assessment"}, headers=customer).json()
    pay(client, body)
    none_yet = client.get(f"{API}/library/report.full_assessment/download", headers=customer)
    assert none_yet.status_code == 409 and none_yet.json()["error"]["code"] == "no_results_yet"
    answer(client, customer, "style", STYLE_ROMANTIC)
    report = client.get(f"{API}/library/report.full_assessment/download", headers=customer)
    assert report.status_code == 200 and report.content.startswith(b"%PDF")


def test_premium_subscription_unlocks_guides_and_can_be_cancelled(client, customer, db):
    plans = client.get(f"{API}/shop/plans", headers=customer).json()
    assert {p["key"] for p in plans} == {"customer.premium.monthly", "customer.premium.annual"}
    assert client.get(f"{API}/shop/plans", params={"audience": "consultant"}).status_code == 404  # Phase 2 is off
    checkout = client.post(f"{API}/checkout/plan", json={"plan_key": "customer.premium.monthly"}, headers=customer).json()
    pay(client, checkout)
    subs = client.get(f"{API}/me/subscriptions", headers=customer).json()
    assert subs[0]["status"] == "active"
    assert client.get(f"{API}/library/guide.lip_blush.winter/download", headers=customer).status_code == 200
    assert client.post(f"{API}/checkout/plan", json={"plan_key": "customer.premium.annual"}, headers=customer).status_code == 409

    cancelled = client.post(f"{API}/me/subscriptions/{subs[0]['id']}/cancel", headers=customer).json()
    assert cancelled["cancel_at_period_end"] is True
    # Access continues until the period ends, then stops.
    assert client.get(f"{API}/library/guide.lip_blush.winter/download", headers=customer).status_code == 200
    end = datetime.fromisoformat(subs[0]["current_period_end"])
    assert commerce.renew_due(db, get_payments(), at=end + timedelta(minutes=1)) == {"expired": 1, "renewal_orders": 0}
    for entitlement in db.scalars(select(Entitlement).where(Entitlement.key == "premium")):
        entitlement.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert client.get(f"{API}/library/guide.lip_blush.winter/download", headers=customer).status_code == 402


def test_renewal_opens_an_order_and_payment_extends_the_period(client, customer, db):
    checkout = client.post(f"{API}/checkout/plan", json={"plan_key": "customer.premium.monthly"}, headers=customer).json()
    pay(client, checkout)
    subscription = db.scalars(select(Subscription)).one()
    first_end = subscription.current_period_end
    assert commerce.renew_due(db, get_payments(), at=first_end + timedelta(minutes=1)) == {"expired": 0, "renewal_orders": 1}
    db.commit()
    renewal = db.scalars(select(Order).where(Order.kind == "renewal")).one()
    client.post(f"{API}/sandbox/pay/{renewal.provider_ref}")
    db.expire_all()
    subscription = db.scalars(select(Subscription)).one()
    assert subscription.status == "active" and subscription.current_period_end > first_end


def test_refund_takes_back_the_purchase(client, customer, owner):
    checkout = client.post(f"{API}/checkout/product", json={"product_key": "guide.body.apple"}, headers=customer).json()
    pay(client, checkout)
    assert client.get(f"{API}/library/guide.body.apple/download", headers=customer).status_code == 200
    refunded = client.post(f"{API}/admin/orders/{checkout['order_id']}/refund", headers=owner)
    assert refunded.status_code == 200 and refunded.json()["status"] == "refunded"
    assert client.get(f"{API}/library/guide.body.apple/download", headers=customer).status_code == 402


def test_paid_items_follow_their_switches(client, customer, release):
    assert release(features={"phase1.paid_reports": False}).status_code == 201
    keys = {p["key"] for p in client.get(f"{API}/shop/products", headers=customer).json()}
    assert "report.full_assessment" not in keys and "guide.body.pear" in keys
    assert client.post(f"{API}/checkout/product", json={"product_key": "report.full_assessment"}, headers=customer).status_code == 404
    # Physical products are Phase 3.
    assert not any(k.startswith("physical.") for k in keys)


def test_only_finance_changes_prices(client, owner, db):
    from app.modules.auth import service as auth_service
    from app.tests.conftest import PASSWORD

    auth_service.create_user(db, email="content@example.com", password=PASSWORD, full_name="Content", role_key="content_manager")
    db.commit()
    content = login(client, "content@example.com")
    assert client.patch(f"{API}/admin/products/guide.body.pear", json={"title": {"en": "Pear guide", "ar": "دليل"}}, headers=content).status_code == 200
    assert client.patch(f"{API}/admin/products/guide.body.pear", json={"price_minor": 1}, headers=content).status_code == 403
    assert client.patch(f"{API}/admin/products/guide.body.pear", json={"price_minor": 3500}, headers=owner).status_code == 200


# ---------- retail links (row 36) ----------

def test_retail_items_are_matched_to_results_and_clicks_counted(client, customer, owner, db):
    for retailer, tags in (("A", {"style": ["romantic"]}), ("B", {"style": ["dramatic"]}), ("C", {})):
        response = client.post(f"{API}/admin/retail-items", json={
            "retailer": retailer, "title": {"en": f"Dress {retailer}", "ar": "فستان"},
            "url": f"https://shop.example/{retailer}", "tags": tags}, headers=owner)
        assert response.status_code == 201
    answer(client, customer, "style", STYLE_ROMANTIC)
    found = client.get(f"{API}/shop/retail", headers=customer).json()
    assert found["based_on"]["style"] == "romantic"
    assert [i["retailer"] for i in found["items"]] == ["A", "C"]  # dramatic item left out, match first
    go = client.get(f"{API}/shop/retail/{found['items'][0]['id']}/go", headers=customer, follow_redirects=False)
    assert go.status_code == 303 and go.headers["location"] == "https://shop.example/A"
    assert db.scalar(select(RetailItem.clicks).where(RetailItem.retailer == "A")) == 1


def test_registration_stores_the_eligibility_facts(client, db):
    register(client, "row@example.com", **ELIGIBLE)
    profile = db.scalars(select(CustomerProfile).where(CustomerProfile.country_code == "AE")).all()
    assert [(p.gender, p.date_of_birth, p.eligibility_status) for p in profile if p.date_of_birth == date(1990, 5, 1)]


def test_download_links_open_the_pdf_without_the_app_token_and_expire(client, customer, monkeypatch):
    from app.core import security

    client.post(f"{API}/library/guide.palette.winter/claim", headers=customer)
    path = client.get(f"{API}/library/guide.palette.winter/link", headers=customer).json()["path"]
    opened = client.get(path)  # no Authorization header, like a browser
    assert opened.status_code == 200 and opened.content.startswith(b"%PDF")
    # Not usable as an access token, and not for another document.
    token = path.rsplit("/", 1)[1]
    assert client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.get(f"{API}/library/guide.body.pear/link", headers=customer).status_code == 402
    monkeypatch.setattr(security, "DOWNLOAD_MINUTES", -1)
    expired = client.get(f"{API}/library/guide.palette.winter/link", headers=customer).json()["path"]
    assert client.get(expired).status_code == 404


def test_retail_click_returns_the_link(client, customer, owner):
    item = client.post(f"{API}/admin/retail-items", json={"retailer": "A", "title": {"en": "Dress", "ar": "فستان"},
                       "url": "https://shop.example/a"}, headers=owner).json()
    assert client.post(f"{API}/shop/retail/{item['id']}/click", headers=customer).json() == {"url": "https://shop.example/a"}
