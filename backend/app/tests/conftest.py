import os

os.environ["IC_ENV"] = "testing"
os.environ["IC_DATABASE_URL"] = os.environ.get(
    "IC_TEST_DATABASE_URL", "postgresql+psycopg://ic:ic@localhost:5432/ic_test"
)

import pytest  # noqa: E402
from fastapi import APIRouter, Depends  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import models  # noqa: E402, F401
from app.database.base import Base  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.auth import service as auth_service  # noqa: E402
from app.modules.feature_flags.guard import require_feature  # noqa: E402
from app.modules.phase_management.seed import seed  # noqa: E402

PASSWORD = "correct-horse-battery"
# Eligibility facts for a test customer: an adult woman in the UAE.
ELIGIBLE = {"date_of_birth": "1990-05-01", "gender": "female", "country_code": "AE"}
ADMIN = "/api/v1/admin/phase-management"

# Business modules arrive in later milestones. Until then these test-only
# routes stand in for "an endpoint that belongs to feature X" so the guard is
# exercised exactly the way real module routers will use it.
PROBES = {
    "p1": "phase1.face_shape",
    "p1-enh": "phase1.eyewear",
    "p2": "phase2.booking",
    "p2-makeup": "phase2.makeup_audit",
    "p3": "phase3.geo_promotions",
}


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def _fresh_data(_schema):
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    with SessionLocal() as db:
        seed(db)
        auth_service.create_user(
            db, email="owner@example.com", password=PASSWORD, full_name="Owner", role_key="super_admin"
        )
        auth_service.create_user(
            db, email="client-admin@example.com", password=PASSWORD, full_name="Client Admin", role_key="admin"
        )
        customer = auth_service.create_user(
            db, email="customer@example.com", password=PASSWORD, full_name="Customer", language="ar"
        )
        make_eligible(db, customer)
        db.commit()


def make_eligible(db, user):
    from datetime import date

    from app.modules.users.models import CustomerProfile

    db.add(CustomerProfile(user_id=user.id, date_of_birth=date(1990, 5, 1), gender="female", country_code="AE",
                           eligibility_status="eligible", eligibility_reasons=[], identity_status="verified"))
    db.flush()


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    app = create_app()
    probes = APIRouter(prefix="/api/v1/_probe")
    for path, key in PROBES.items():
        probes.add_api_route(
            f"/{path}", lambda: {"ok": True}, dependencies=[Depends(require_feature(key))], methods=["GET"]
        )
    app.include_router(probes)
    with TestClient(app) as test_client:
        yield test_client


def login(client, email):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def owner(client):
    return login(client, "owner@example.com")


@pytest.fixture
def customer(client):
    return login(client, "customer@example.com")


@pytest.fixture
def release(client, owner):
    """Create a release as the Super Admin; returns the HTTP response."""

    def _release(note="test release", **changes):
        return client.post(f"{ADMIN}/releases", json={"note": note, **changes}, headers=owner)

    return _release
