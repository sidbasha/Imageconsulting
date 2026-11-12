"""Phase 2 and 3 marketplace flows, end to end through the API."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.integrations.storage import LocalStorage, get_storage
from app.modules.commerce.models import Order
from app.modules.marketplace.models import Booking
from app.tests.conftest import ELIGIBLE, login
from app.tests.test_photo_analysis import FACE_JPEG
from app.tests.test_users_and_commerce import pay, register

API = "/api/v1"
SEASONAL_WINTER = {"jewellery": "silver", "veins": "blue", "depth": "deep", "clarity": "bright"}


@pytest.fixture
def storage(client, tmp_path):
    store = LocalStorage(str(tmp_path))
    client.app.dependency_overrides[get_storage] = lambda: store
    return store


@pytest.fixture
def phase2(release):
    assert release(phases={"phase2": True}).status_code == 201


def in_days(days: float, hour: int = 10) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


def make_stylist(client, owner, email="stylist@example.com", city="Dubai", lat=25.2, lng=55.27, kinds=("consultation",), price=25000, membership=True):
    headers = register(client, email, **ELIGIBLE)
    application = {"display_name": email.split("@")[0].title(), "bio": "Image consultant", "city": city,
                   "latitude": lat, "longitude": lng, "languages": ["en", "ar"]}
    assert client.put(f"{API}/stylist/application", json=application, headers=headers).status_code == 200
    upload = client.post(f"{API}/stylist/application/credentials", data={"kind": "certification", "title": "AICI"},
                         files={"file": ("cert.pdf", b"%PDF-1.4 cert", "application/pdf")}, headers=headers)
    assert upload.status_code == 201, upload.text
    assert client.post(f"{API}/stylist/application/submit", headers=headers).json()["status"] == "submitted"
    queue = client.get(f"{API}/admin/stylists", headers=owner).json()
    mine = next(p for p in queue if p["display_name"] == application["display_name"])
    client.post(f"{API}/admin/stylists/credentials/{mine['credentials'][0]['id']}/review", json={"approve": True}, headers=owner)
    decided = client.post(f"{API}/admin/stylists/{mine['id']}/decision", json={"approve": True}, headers=owner)
    assert decided.json()["status"] == "approved"
    headers = login_password(client, email)
    if membership:  # row 40: annual participation fee
        checkout = client.post(f"{API}/checkout/plan", json={"plan_key": "consultant.annual"}, headers=headers)
        assert checkout.status_code == 201, checkout.text
        pay(client, checkout.json())
    else:
        return {"headers": headers, "profile_id": mine["id"]}
    services = {}
    for kind in kinds:
        mode = "in_person" if kind == "personal_shopper_day" else "online"
        created = client.post(f"{API}/stylist/services", json={"kind": kind, "title": kind.replace("_", " ").title(),
                              "price_minor": price, "duration_minutes": 30 if mode == "online" else 480, "mode": mode}, headers=headers)
        assert created.status_code == 201, created.text
        services[kind] = created.json()["id"]
    slots = client.post(f"{API}/stylist/slots", json={"starts": [in_days(3), in_days(3, 11), in_days(4)]}, headers=headers).json()
    return {"headers": headers, "profile_id": mine["id"], "services": services, "slots": [s["id"] for s in slots]}


def login_password(client, email):
    token = client.post(f"{API}/auth/login", json={"email": email, "password": "a-long-enough-password"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def book_and_pay(client, customer, stylist, kind="consultation", slot=0, **extra):
    booked = client.post(f"{API}/bookings", json={"service_id": stylist["services"][kind], "slot_id": stylist["slots"][slot], **extra},
                         headers=customer)
    assert booked.status_code == 201, booked.text
    body = booked.json()
    if body["checkout"]:
        assert pay(client, body["checkout"]).json()["status"] == "paid"
    return body["booking"]["id"]


# ---------- applications and vetting (15-17, 53-54) ----------

def test_marketplace_is_closed_until_phase2(client, customer):
    assert client.get(f"{API}/stylists", headers=customer).status_code == 404
    assert client.get(f"{API}/stylist/application", headers=customer).status_code == 404


def test_application_needs_credentials_and_manual_approval(client, owner, phase2, storage):
    headers = register(client, "applicant@example.com", **ELIGIBLE)
    client.put(f"{API}/stylist/application", json={"bio": "Hello", "city": "Dubai"}, headers=headers)
    early = client.post(f"{API}/stylist/application/submit", headers=headers)
    assert early.status_code == 422 and early.json()["error"]["detail"] == {"missing": ["credentials"]}
    client.post(f"{API}/stylist/application/credentials", data={"kind": "business_license", "title": "Licence"},
                files={"file": ("l.png", b"\x89PNG", "image/png")}, headers=headers)
    client.post(f"{API}/stylist/application/submit", headers=headers)
    # Under review: cannot edit; cannot offer services.
    assert client.put(f"{API}/stylist/application", json={"bio": "x"}, headers=headers).status_code == 409
    assert client.post(f"{API}/stylist/services", json={"kind": "consultation", "title": "C", "price_minor": 1}, headers=headers).status_code == 403
    profile = client.get(f"{API}/admin/stylists", headers=owner).json()[0]
    # Approval requires an accepted credential (manual vetting).
    assert client.post(f"{API}/admin/stylists/{profile['id']}/decision", json={"approve": True}, headers=owner).status_code == 409
    file = client.get(f"{API}/admin/stylists/credentials/{profile['credentials'][0]['id']}/file", headers=owner)
    assert file.content == b"\x89PNG"
    rejected = client.post(f"{API}/admin/stylists/{profile['id']}/decision", json={"approve": False, "note": "Licence unreadable"}, headers=owner)
    assert rejected.json()["status"] == "rejected"
    assert client.get(f"{API}/stylist/application", headers=headers).json()["review_note"] == "Licence unreadable"


def test_stylist_manager_can_vet_but_customer_cannot(client, phase2, db):
    from app.modules.auth import service as auth_service
    from app.tests.conftest import PASSWORD

    auth_service.create_user(db, email="sm@example.com", password=PASSWORD, full_name="SM", role_key="stylist_manager")
    db.commit()
    assert client.get(f"{API}/admin/stylists", headers=login(client, "sm@example.com")).status_code == 200
    assert client.get(f"{API}/admin/stylists", headers=login(client, "customer@example.com")).status_code == 403


# ---------- discovery, booking, payment (18, 19, 41) ----------

def test_book_pay_consult_report_review(client, owner, customer, phase2, storage, db):
    stylist = make_stylist(client, owner)
    found = client.get(f"{API}/stylists", headers=customer).json()
    assert [s["display_name"] for s in found] == ["Stylist"]
    own = client.get(f"{API}/stylist/slots", headers=stylist["headers"]).json()
    assert len(own) == 3 and not any(s["booked"] for s in own)
    detail = client.get(f"{API}/stylists/{stylist['profile_id']}", headers=customer).json()
    assert len(detail["slots"]) == 3 and detail["services"][0]["price_minor"] == 25000

    booked = client.post(f"{API}/bookings", json={"service_id": stylist["services"]["consultation"], "slot_id": stylist["slots"][0]}, headers=customer).json()
    assert booked["booking"]["status"] == "pending_payment" and booked["checkout"]["amount_minor"] == 25000
    # The slot is held while she pays.
    assert len(client.get(f"{API}/stylists/{stylist['profile_id']}", headers=customer).json()["slots"]) == 2
    other = register(client, "other@example.com", **ELIGIBLE)
    pay(client, booked["checkout"])
    booking = client.get(f"{API}/bookings/{booked['booking']['id']}", headers=customer).json()
    assert booking["status"] == "confirmed" and booking["paid_with"] == "payment"

    # Consultation opened; the customer shares her photo, the stylist reports.
    consultation = client.get(f"{API}/consultations", headers=customer).json()[0]
    assert consultation["kind"] == "consultation" and consultation["role"] == "customer"
    upload = client.post(f"{API}/consultations/{consultation['id']}/files", data={"purpose": "outfit", "consent": "true", "caption": "Dinner look"},
                         files={"file": ("o.jpg", FACE_JPEG, "image/jpeg")}, headers=customer)
    assert upload.status_code == 201
    template = client.get(f"{API}/consultations/{consultation['id']}/report/template", headers=stylist["headers"]).json()
    assert [s["key"] for s in template["sections"]] == ["suitability", "explanation", "recommendations"]
    bad = client.put(f"{API}/consultations/{consultation['id']}/report", json={"content": {"suitability": "great"}}, headers=stylist["headers"])
    assert bad.status_code == 422
    draft = {"suitability": "adjust", "explanation": "Warm tones suit you."}
    client.put(f"{API}/consultations/{consultation['id']}/report", json={"content": draft}, headers=stylist["headers"])
    assert client.get(f"{API}/consultations/{consultation['id']}", headers=customer).json()["report"] is None  # not yet delivered
    incomplete = client.post(f"{API}/consultations/{consultation['id']}/report/deliver", headers=stylist["headers"])
    assert incomplete.status_code == 422 and "recommendations" in incomplete.json()["error"]["detail"]
    client.put(f"{API}/consultations/{consultation['id']}/report", json={"content": {**draft, "recommendations": ["Camel coat"]}}, headers=stylist["headers"])
    assert client.post(f"{API}/consultations/{consultation['id']}/report/deliver", headers=stylist["headers"]).status_code == 200
    seen = client.get(f"{API}/consultations/{consultation['id']}", headers=customer).json()["report"]
    assert seen["sections"][0]["value"]["label"] == "مناسب مع تعديلات"  # Arabic for this customer
    report_pdf = client.get(f"{API}/consultations/{consultation['id']}/report.pdf", headers=customer)
    assert report_pdf.content.startswith(b"%PDF")
    # Nobody else can see it.
    assert client.get(f"{API}/consultations/{consultation['id']}", headers=other).status_code == 404

    # Testimonial only after completion.
    t = {"rating": 5, "text": "Wonderful"}
    assert client.post(f"{API}/bookings/{booking['id']}/testimonial", json=t, headers=customer).status_code == 409
    client.post(f"{API}/stylist/bookings/{booking['id']}/complete", headers=stylist["headers"])
    assert client.post(f"{API}/bookings/{booking['id']}/testimonial", json=t, headers=customer).status_code == 201
    assert client.post(f"{API}/bookings/{booking['id']}/testimonial", json=t, headers=customer).status_code == 409
    profile = client.get(f"{API}/stylists/{stylist['profile_id']}", headers=customer).json()
    assert profile["rating_avg"] == 5 and profile["testimonials"][0]["text"] == "Wonderful"


def test_unpaid_hold_lapses_and_late_payment_is_marked_for_refund(client, owner, customer, phase2, db):
    stylist = make_stylist(client, owner)
    booked = client.post(f"{API}/bookings", json={"service_id": stylist["services"]["consultation"], "slot_id": stylist["slots"][0]}, headers=customer).json()
    db.execute(Booking.__table__.update().values(hold_expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    db.commit()
    assert len(client.get(f"{API}/stylists/{stylist['profile_id']}", headers=customer).json()["slots"]) == 3  # slot back
    pay(client, booked["checkout"])
    assert client.get(f"{API}/bookings/{booked['booking']['id']}", headers=customer).json()["status"] == "expired"
    assert db.scalar(select(Order.status).where(Order.id == booked["checkout"]["order_id"])) == "refund_due"


def test_double_booking_a_slot_is_refused(client, owner, customer, phase2):
    stylist = make_stylist(client, owner)
    book_and_pay(client, customer, stylist)
    other = register(client, "second@example.com", **ELIGIBLE)
    from app.modules.users.models import CustomerProfile  # noqa: F401
    client.post(f"{API}/identity/uae-pass/complete", headers=other, json={"code": _uae_code("second")})
    again = client.post(f"{API}/bookings", json={"service_id": stylist["services"]["consultation"], "slot_id": stylist["slots"][0]}, headers=other)
    assert again.status_code == 409 and again.json()["error"]["code"] == "slot_unavailable"


def _uae_code(subject):
    from app.integrations.uae_pass import get_uae_pass

    return get_uae_pass().issue_code(subject=subject, gender="female", date_of_birth="1990-05-01")


def test_booking_needs_a_verified_identity(client, owner, phase2):
    stylist = make_stylist(client, owner)
    headers = register(client, "unverified@example.com", **ELIGIBLE)
    attempt = client.post(f"{API}/bookings", json={"service_id": stylist["services"]["consultation"], "slot_id": stylist["slots"][0]}, headers=headers)
    assert attempt.status_code == 403 and attempt.json()["error"]["code"] == "identity_not_verified"


def test_customer_cancels_in_time_and_is_refunded(client, owner, customer, phase2, db):
    stylist = make_stylist(client, owner)
    booking_id = book_and_pay(client, customer, stylist)
    cancelled = client.post(f"{API}/bookings/{booking_id}/cancel", headers=customer).json()
    assert cancelled["status"] == "cancelled" and cancelled["cancelled_by"] == "customer"
    order = db.scalars(select(Order).where(Order.kind == "booking")).one()
    assert order.status == "refunded"
    assert len(client.get(f"{API}/stylists/{stylist['profile_id']}", headers=customer).json()["slots"]) == 3


def test_late_cancellation_is_refused(client, owner, customer, phase2, db):
    stylist = make_stylist(client, owner)
    booking_id = book_and_pay(client, customer, stylist)
    client.put(f"{API}/admin/settings/booking.cancel_hours", json={"value": 24 * 7}, headers=owner)
    assert client.post(f"{API}/bookings/{booking_id}/cancel", headers=customer).status_code == 409
    # The stylist can still cancel, and the customer is refunded.
    assert client.post(f"{API}/bookings/{booking_id}/cancel", headers=stylist["headers"]).json()["cancelled_by"] == "stylist"


# ---------- messaging safeguards (30-33, 58) ----------

def test_messages_with_contact_details_are_blocked_and_counted(client, owner, customer, phase2):
    stylist = make_stylist(client, owner)
    # No booking yet: no thread.
    assert client.post(f"{API}/messages", json={"stylist_id": stylist["profile_id"]}, headers=customer).status_code == 409
    book_and_pay(client, customer, stylist)
    thread = client.post(f"{API}/messages", json={"stylist_id": stylist["profile_id"]}, headers=customer).json()

    ok = client.post(f"{API}/messages/{thread['id']}", json={"body": "Looking forward to Tuesday!"}, headers=customer).json()
    assert ok["warning"] is None
    sneaky = client.post(f"{API}/messages/{thread['id']}", json={"body": "واتساب ٠٥٠١٢٣٤٥٦٧"}, headers=customer).json()
    assert sneaky["warning"]["code"] == "contact_details_blocked" and sneaky["warning"]["kinds"] == ["phone", "social"]
    assert sneaky["warning"]["consequence"] == "warning"
    # The stylist never sees it; the sender sees it as not delivered.
    theirs = client.get(f"{API}/messages/{thread['id']}", headers=stylist["headers"]).json()
    assert [m["body"] for m in theirs] == ["Looking forward to Tuesday!"]
    mine = client.get(f"{API}/messages/{thread['id']}", headers=customer).json()
    assert mine[-1]["status"] == "not_delivered"

    for text in ("email me sara at gmail dot com", "my insta is @sara.style"):
        last = client.post(f"{API}/messages/{thread['id']}", json={"body": text}, headers=customer).json()
    assert last["warning"]["consequence"] == "suspended"
    blocked = client.post(f"{API}/messages/{thread['id']}", json={"body": "hello?"}, headers=customer)
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "messaging_suspended"

    # A moderator dismisses one as a false positive: it is delivered after all; then lifts the suspension.
    queue = client.get(f"{API}/admin/moderation/violations", headers=owner).json()
    assert len(queue) == 3 and queue[0]["user_violations"] == 3
    client.post(f"{API}/admin/moderation/violations/{queue[2]['id']}", json={"uphold": False}, headers=owner)
    assert any(m["body"] == "my insta is @sara.style" for m in client.get(f"{API}/messages/{thread['id']}", headers=stylist["headers"]).json())
    client.post(f"{API}/admin/moderation/users/{queue[0]['user']['id']}/lift", json={"note": "Reviewed"}, headers=owner)
    assert client.post(f"{API}/messages/{thread['id']}", json={"body": "Thanks"}, headers=customer).status_code == 201


def test_repeated_violations_deactivate_the_account(client, owner, customer, phase2):
    client.put(f"{API}/admin/settings/moderation.ban_after", json={"value": 2}, headers=owner)
    stylist = make_stylist(client, owner)
    book_and_pay(client, customer, stylist)
    thread = client.post(f"{API}/messages", json={"stylist_id": stylist["profile_id"]}, headers=customer).json()
    client.post(f"{API}/messages/{thread['id']}", json={"body": "050 123 4567"}, headers=customer)
    last = client.post(f"{API}/messages/{thread['id']}", json={"body": "sara@mail.com"}, headers=customer).json()
    assert last["warning"]["consequence"] == "banned"
    assert client.get(f"{API}/messages", headers=customer).status_code == 401  # account deactivated


# ---------- audits, makeup audit rule, workspace and metering (21-23, 27-29) ----------

def test_occasion_audit_needs_intake_and_makeup_audit_needs_colour(client, owner, customer, phase2, storage):
    stylist = make_stylist(client, owner, kinds=("occasion_audit", "makeup_audit"))
    book_and_pay(client, customer, stylist, "occasion_audit", slot=0)
    book_and_pay(client, customer, stylist, "makeup_audit", slot=1)
    by_kind = {c["kind"]: c for c in client.get(f"{API}/consultations", headers=customer).json()}
    occasion = by_kind["occasion_audit"]
    assert occasion["required_intake"] == ["occasion", "role", "personality"]
    missing = client.put(f"{API}/consultations/{occasion['id']}/intake", json={"intake": {"occasion": "Wedding"}}, headers=customer)
    assert missing.json()["error"]["detail"] == {"missing": ["role", "personality"]}
    full = {"occasion": "Wedding", "role": "Guest", "personality": "Calm"}
    assert client.put(f"{API}/consultations/{occasion['id']}/intake", json={"intake": full}, headers=customer).status_code == 200

    makeup = by_kind["makeup_audit"]
    product = {"purpose": "product", "consent": "true", "caption": "Red lipstick"}
    no_colour = client.post(f"{API}/consultations/{makeup['id']}/files", data=product, files={"file": ("p.jpg", FACE_JPEG, "image/jpeg")}, headers=customer)
    assert no_colour.status_code == 409 and no_colour.json()["error"]["code"] == "seasonal_color_required"
    client.post(f"{API}/assessments/seasonal_color/responses", json={"answers": SEASONAL_WINTER}, headers=customer)
    item = client.post(f"{API}/consultations/{makeup['id']}/files", data=product, files={"file": ("p.jpg", FACE_JPEG, "image/jpeg")}, headers=customer).json()
    verdict = client.put(f"{API}/consultations/{makeup['id']}/files/{item['id']}/verdict", json={"verdict": "suits", "note": "Blue-red"}, headers=stylist["headers"])
    assert verdict.json()["verdict"] == {"verdict": "suits", "note": "Blue-red"}
    # Product recognition is not wired to a provider: it says so (when released).
    assert client.post(f"{API}/consultations/{makeup['id']}/files/{item['id']}/recognise", headers=stylist["headers"]).status_code in (404, 503)


def test_colour_workspace_meters_credits_and_drapes(client, owner, customer, phase2, storage):
    stylist = make_stylist(client, owner, kinds=("expert_color",))
    book_and_pay(client, customer, stylist, "expert_color")
    consultation = client.get(f"{API}/consultations", headers=customer).json()[0]
    face = client.post(f"{API}/consultations/{consultation['id']}/files", data={"purpose": "face", "consent": "true"},
                       files={"file": ("f.jpg", FACE_JPEG, "image/jpeg")}, headers=customer).json()
    # The customer cannot use the consultant tool.
    assert client.post(f"{API}/workspace/{consultation['id']}/open", headers=customer).status_code == 403
    # Metering is on with Phase 2: no credits, no workspace.
    no_credit = client.post(f"{API}/workspace/{consultation['id']}/open", headers=stylist["headers"])
    assert no_credit.status_code == 402
    checkout = client.post(f"{API}/checkout/product", json={"product_key": "credits.workspace.10"}, headers=stylist["headers"]).json()
    pay(client, checkout)
    assert client.post(f"{API}/workspace/{consultation['id']}/open", headers=stylist["headers"]).json() == {"open": True, "credits_used": 1}
    assert client.post(f"{API}/workspace/{consultation['id']}/open", headers=stylist["headers"]).json()["credits_used"] == 1  # same client: once
    credits = {e["key"]: e["quantity"] for e in client.get(f"{API}/me/entitlements", headers=stylist["headers"]).json()}
    assert credits["workspace.credits"] == 9

    drape = client.get(f"{API}/workspace/{consultation['id']}/drape", params={"file_id": face["id"], "colour": "#1f3a93"}, headers=stylist["headers"])
    assert drape.status_code == 200 and drape.content[:2] == b"\xff\xd8"
    grid = client.post(f"{API}/workspace/{consultation['id']}/compare", json={"file_id": face["id"], "colours": ["#1f3a93", "#c0392b", "#f1c40f"]}, headers=stylist["headers"])
    assert grid.status_code == 200
    reading = client.post(f"{API}/workspace/{consultation['id']}/indicative", params={"file_id": face["id"]}, headers=stylist["headers"]).json()
    assert reading["indicative"] is True and reading["season"] in ("spring", "summer", "autumn", "winter")

    # Expert colour report has its own required fields (row 24).
    template = client.get(f"{API}/consultations/{consultation['id']}/report/template", headers=stylist["headers"]).json()
    assert {"temperature", "contrast", "metals", "palette"} <= {s["key"] for s in template["sections"]}


# ---------- rewards (43, 44) ----------

def test_points_are_earned_and_redeemed_for_a_free_consultation(client, owner, customer, phase2, db):
    from app.modules.rewards.models import PointsEntry

    client.post(f"{API}/assessments/seasonal_color/responses", json={"answers": SEASONAL_WINTER}, headers=customer)
    client.post(f"{API}/assessments/seasonal_color/responses", json={"answers": SEASONAL_WINTER}, headers=customer)  # once only
    assert client.get(f"{API}/rewards", headers=customer).json()["balance"] == 20
    assert client.post(f"{API}/rewards/redeem/consultation_30", headers=customer).status_code == 409
    db.add(PointsEntry(user_id=_user_id(db, "customer@example.com"), delta=1000, event="adjustment"))
    db.commit()
    assert client.post(f"{API}/rewards/redeem/consultation_30", headers=customer).json()["balance"] == 20

    stylist = make_stylist(client, owner)
    booking = client.post(f"{API}/bookings", json={"service_id": stylist["services"]["consultation"], "slot_id": stylist["slots"][0], "use_reward": True}, headers=customer).json()
    assert booking["checkout"] is None and booking["booking"]["status"] == "confirmed" and booking["booking"]["paid_with"] == "reward"
    # The credit is spent.
    second = client.post(f"{API}/bookings", json={"service_id": stylist["services"]["consultation"], "slot_id": stylist["slots"][1], "use_reward": True}, headers=customer)
    assert second.status_code == 402
    # Cancelling gives the credit back.
    client.post(f"{API}/bookings/{booking['booking']['id']}/cancel", headers=customer)
    keys = {e["key"]: e["quantity"] for e in client.get(f"{API}/me/entitlements", headers=customer).json()}
    assert keys.get("reward.consultation") == 1


def _user_id(db, email):
    from app.modules.auth.models import User

    return db.scalar(select(User.id).where(User.email == email))


def test_purchases_earn_points(client, customer):
    checkout = client.post(f"{API}/checkout/product", json={"product_key": "guide.body.pear"}, headers=customer).json()
    pay(client, checkout)
    assert client.get(f"{API}/rewards", headers=customer).json()["balance"] == 29  # 1 point per AED, draft rule


# ---------- membership, promotion, ranking (40, 42, 66) ----------

def test_paid_featuring_lifts_a_stylist_in_discovery(client, owner, customer, phase2):
    a = make_stylist(client, owner, "amal@example.com")
    b = make_stylist(client, owner, "basma@example.com")
    order = [s["display_name"] for s in client.get(f"{API}/stylists", headers=customer).json()]
    assert order == ["Amal", "Basma"]
    bought = client.post(f"{API}/stylist/promotions", json={"starts_at": datetime.now(UTC).isoformat(), "days": 7}, headers=b["headers"]).json()
    assert bought["checkout"]["amount_minor"] == 35000
    pay(client, bought["checkout"])
    pending = client.get(f"{API}/admin/promotions/campaigns", params={"status_filter": "pending_review"}, headers=owner).json()
    client.post(f"{API}/admin/promotions/campaigns/{pending[0]['id']}/status", json={"status": "active"}, headers=owner)
    found = client.get(f"{API}/stylists", headers=customer).json()
    assert [s["display_name"] for s in found] == ["Basma", "Amal"] and found[0]["promoted"] is True
    _ = a


def test_consultant_membership_is_required_to_offer_services_and_be_listed(client, owner, customer, phase2):
    stylist = make_stylist(client, owner, membership=False)
    service = {"kind": "consultation", "title": "C", "price_minor": 100}
    blocked = client.post(f"{API}/stylist/services", json=service, headers=stylist["headers"])
    assert blocked.status_code == 402 and blocked.json()["error"]["code"] == "membership_required"
    # Customers cannot buy the consultant plan.
    assert client.post(f"{API}/checkout/plan", json={"plan_key": "consultant.annual"}, headers=customer).status_code == 403
    checkout = client.post(f"{API}/checkout/plan", json={"plan_key": "consultant.annual"}, headers=stylist["headers"]).json()
    assert checkout["amount_minor"] == 150000
    pay(client, checkout)
    assert client.post(f"{API}/stylist/services", json=service, headers=stylist["headers"]).status_code == 201
    client.post(f"{API}/stylist/slots", json={"starts": [in_days(2)]}, headers=stylist["headers"])
    assert len(client.get(f"{API}/stylists", headers=customer).json()) == 1


# ---------- Phase 3: personal shopper, location, brand ads, vouchers (46, 47, 49-51) ----------

def test_phase3_personal_shopper_location_ads_and_vouchers(client, owner, customer, release):
    assert release(phases={"phase2": True, "phase3": True}).status_code == 201
    near = make_stylist(client, owner, "near@example.com", lat=25.20, lng=55.27, kinds=("consultation", "personal_shopper_day"))
    make_stylist(client, owner, "far@example.com", city="Abu Dhabi", lat=24.45, lng=54.38)

    nearby = client.get(f"{API}/stylists", params={"lat": 25.19, "lng": 55.28, "radius_km": 20}, headers=customer).json()
    assert [s["display_name"] for s in nearby] == ["Near"] and nearby[0]["distance_km"] < 5

    no_address = client.post(f"{API}/bookings", json={"service_id": near["services"]["personal_shopper_day"], "slot_id": near["slots"][2]}, headers=customer)
    assert no_address.status_code == 422
    booking_id = book_and_pay(client, customer, near, "personal_shopper_day", slot=2, address={"line1": "Dubai Mall", "city": "Dubai"})
    assert client.get(f"{API}/bookings/{booking_id}", headers=customer).json()["address"]["line1"] == "Dubai Mall"

    now = datetime.now(UTC)
    campaign = {"advertiser_name": "Salon A", "placement": "home_banner", "title": {"en": "20% off", "ar": "خصم ٢٠٪"},
                "target_url": "https://salon.example", "starts_at": (now - timedelta(hours=1)).isoformat(),
                "ends_at": (now + timedelta(days=5)).isoformat()}
    client.post(f"{API}/admin/promotions/campaigns", json=campaign, headers=owner)
    client.post(f"{API}/admin/promotions/campaigns", json={**campaign, "advertiser_name": "Salon Abu Dhabi",
                "latitude": 24.45, "longitude": 54.38, "radius_km": 10}, headers=owner)
    in_dubai = client.get(f"{API}/promotions", params={"lat": 25.2, "lng": 55.27}, headers=customer).json()
    assert [c["advertiser"] for c in in_dubai] == ["Salon A"] and in_dubai[0]["title"] == "خصم ٢٠٪"
    in_abu_dhabi = client.get(f"{API}/promotions", params={"lat": 24.46, "lng": 54.37}, headers=customer).json()
    assert {c["advertiser"] for c in in_abu_dhabi} == {"Salon A", "Salon Abu Dhabi"}

    voucher = {"partner_name": "Salon A", "title": {"en": "Free blow-dry", "ar": "تصفيف مجاني"}, "code": "IC-BLOW",
               "starts_at": (now - timedelta(hours=1)).isoformat(), "ends_at": (now + timedelta(days=5)).isoformat(), "max_claims": 1}
    client.post(f"{API}/admin/promotions/vouchers", json=voucher, headers=owner)
    listed = client.get(f"{API}/vouchers", headers=customer).json()
    assert listed[0]["code"] is None  # the code is shown only once claimed
    claimed = client.post(f"{API}/vouchers/{listed[0]['id']}/claim", headers=customer).json()
    assert claimed["code"] == "IC-BLOW"
    other = register(client, "late@example.com", **ELIGIBLE)
    assert client.post(f"{API}/vouchers/{listed[0]['id']}/claim", headers=other).status_code == 409


def test_turning_phase2_off_closes_the_marketplace_and_keeps_data(client, owner, customer, release, db):
    assert release(phases={"phase2": True}).status_code == 201
    stylist = make_stylist(client, owner)
    book_and_pay(client, customer, stylist)
    assert release(phases={"phase2": False}).status_code == 201
    for path in ("/stylists", "/bookings", "/consultations", "/messages"):
        assert client.get(f"{API}{path}", headers=customer).status_code == 404, path
    assert db.scalar(select(Booking.status)) == "confirmed"
    assert release(phases={"phase2": True}).status_code == 201
    assert client.get(f"{API}/bookings", headers=customer).json()[0]["status"] == "confirmed"
