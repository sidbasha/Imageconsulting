from app.tests.conftest import PASSWORD

NEW_USER = {"email": "New.User@Example.com", "password": "a-long-enough-password", "full_name": "New User"}


def test_register_login_and_profile(client):
    response = client.post("/api/v1/auth/register", json=NEW_USER)
    assert response.status_code == 201
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    me = client.get("/api/v1/users/me", headers=headers).json()
    assert me["email"] == "new.user@example.com" and me["role"] == "customer" and me["preferred_language"] == "en"

    login = client.post("/api/v1/auth/login", json={"email": NEW_USER["email"], "password": NEW_USER["password"]})
    assert login.status_code == 200


def test_register_rejects_duplicates_and_weak_passwords(client):
    client.post("/api/v1/auth/register", json=NEW_USER)
    assert client.post("/api/v1/auth/register", json=NEW_USER).json()["error"]["code"] == "email_exists"
    assert client.post("/api/v1/auth/register", json={**NEW_USER, "email": "x@example.com", "password": "short"}).status_code == 422


def test_registration_cannot_choose_a_role(client):
    response = client.post("/api/v1/auth/register", json={**NEW_USER, "role": "super_admin", "role_key": "super_admin"})
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/api/v1/users/me", headers=headers).json()["role"] == "customer"


def test_wrong_password_and_missing_token(client):
    response = client.post("/api/v1/auth/login", json={"email": "customer@example.com", "password": "wrong-password"})
    assert response.status_code == 401 and response.json()["error"]["code"] == "invalid_credentials"
    assert client.get("/api/v1/users/me").status_code == 401
    assert client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_refresh_token_rotates_and_works_once(client):
    tokens = client.post("/api/v1/auth/login", json={"email": "customer@example.com", "password": PASSWORD}).json()
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200 and rotated.json()["refresh_token"] != tokens["refresh_token"]
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    # A refresh token is not accepted as an access token.
    assert client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}).status_code == 401


def test_logout_revokes_the_refresh_token(client):
    tokens = client.post("/api/v1/auth/login", json={"email": "customer@example.com", "password": PASSWORD}).json()
    assert client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_case07_case08_language_switch_changes_api_messages(client, customer):
    """API half of mandatory cases 7 and 8. Screen-level RTL/LTR checks belong
    to the mobile and admin milestones."""
    arabic = client.get("/api/v1/admin/phase-management/state", headers=customer)
    assert arabic.headers["content-language"] == "ar"
    assert arabic.json()["error"]["message"] == "ليست لديك صلاحية لتنفيذ هذا الإجراء."

    updated = client.patch("/api/v1/users/me", json={"preferred_language": "en"}, headers=customer)
    assert updated.json()["preferred_language"] == "en"
    english = client.get("/api/v1/admin/phase-management/state", headers=customer)
    assert english.json()["error"]["message"] == "You do not have permission to do this."

    client.patch("/api/v1/users/me", json={"preferred_language": "ar"}, headers=customer)
    assert client.get("/api/v1/admin/phase-management/state", headers=customer).headers["content-language"] == "ar"
    assert client.patch("/api/v1/users/me", json={"preferred_language": "fr"}, headers=customer).status_code == 422


def test_anonymous_requests_use_accept_language(client):
    response = client.get("/api/v1/users/me", headers={"Accept-Language": "ar-AE,ar;q=0.9,en;q=0.5"})
    assert response.json()["error"]["message"] == "يجب تسجيل الدخول."
    assert client.get("/api/v1/users/me").json()["error"]["message"] == "You need to sign in."


def test_every_message_exists_in_both_languages():
    import json
    from pathlib import Path

    folder = Path(__file__).resolve().parent.parent / "localization"
    english = json.loads((folder / "en.json").read_text(encoding="utf-8"))
    arabic = json.loads((folder / "ar.json").read_text(encoding="utf-8"))
    assert english.keys() == arabic.keys()
    assert all(arabic.values()) and all(english.values())


def test_every_error_code_has_an_english_and_arabic_message():
    """Any AppError code raised in the code base must be translated in both languages."""
    import json
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    codes = set()
    for path in root.rglob("*.py"):
        if "tests" not in path.parts:
            codes |= set(re.findall(r'AppError\(\s*\d+,\s*"([a-z_]+)"', path.read_text(encoding="utf-8")))
    for language in ("en", "ar"):
        messages = json.loads((root / "localization" / f"{language}.json").read_text(encoding="utf-8"))
        assert not sorted(codes - messages.keys()), language


def test_profile_lists_permissions_and_cors_allows_the_admin_panel(client, owner):
    me = client.get("/api/v1/users/me", headers=owner).json()
    assert "release.manage" in me["permissions"] and "orders.manage" in me["permissions"]
    customer = client.post("/api/v1/auth/login", json={"email": "customer@example.com", "password": "correct-horse-battery"}).json()
    assert client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {customer['access_token']}"}).json()["permissions"] == []
    preflight = client.options("/api/v1/users/me", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET",
                                                            "Access-Control-Request-Headers": "authorization"})
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.options("/api/v1/users/me", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in other.headers
