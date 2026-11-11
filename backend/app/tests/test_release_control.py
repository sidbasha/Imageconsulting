"""Release control. Test names carry the number of the mandatory release test
case (master prompt section 16) they cover."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.modules.auth.models import User
from app.modules.phase_management import service
from app.modules.phase_management.models import ReleaseConfiguration, ReleaseHistory
from app.tests.conftest import ADMIN, login

FEATURES = "/api/v1/config/features"
PROBE = "/api/v1/_probe"


def probe(client, headers, name):
    return client.get(f"{PROBE}/{name}", headers=headers).status_code


def test_case01_phase1_only_is_the_initial_release(client, customer):
    body = client.get(FEATURES, headers=customer).json()
    assert body["phases"] == ["phase1"]
    assert len(body["features"]) == 20  # 17 "Phase 1" rows + 3 "Phase 1 / enhancement"
    assert all(key.startswith("phase1.") for key in body["features"])
    assert probe(client, customer, "p1") == 200
    assert probe(client, customer, "p2") == 404
    assert probe(client, customer, "p3") == 404


def test_case02_enabling_phase2_keeps_phase1_and_leaves_phase3_off(client, customer, release):
    assert release(phases={"phase2": True}).status_code == 201
    body = client.get(FEATURES, headers=customer).json()
    assert body["phases"] == ["phase1", "phase2"]
    assert len(body["features"]) == 44  # 20 + 24 Phase 2 rows
    assert [probe(client, customer, p) for p in ("p1", "p2", "p3")] == [200, 200, 404]


def test_case03_all_three_phases(client, customer, release):
    assert release(phases={"phase2": True, "phase3": True}).status_code == 201
    body = client.get(FEATURES, headers=customer).json()
    assert body["phases"] == ["phase1", "phase2", "phase3"]
    assert len(body["features"]) == 52  # every discussed feature in the Excel
    assert [probe(client, customer, p) for p in ("p1", "p2", "p3")] == [200, 200, 200]


def test_case04_disable_phase2_after_activation(client, customer, release):
    release(phases={"phase2": True})
    assert probe(client, customer, "p2") == 200
    assert release(phases={"phase2": False}).status_code == 201
    assert [probe(client, customer, p) for p in ("p1", "p2")] == [200, 404]


def test_case05_disable_phase3_after_activation(client, customer, release):
    release(phases={"phase2": True, "phase3": True})
    assert release(phases={"phase3": False}).status_code == 201
    assert [probe(client, customer, p) for p in ("p1", "p2", "p3")] == [200, 200, 404]


def test_case06_disabled_feature_is_blocked_for_direct_api_calls(client, customer):
    # A signed-in customer, an anonymous caller and the client's own admin all get 404.
    assert probe(client, customer, "p2") == 404
    assert probe(client, {}, "p2") == 404
    assert probe(client, login(client, "client-admin@example.com"), "p2") == 404
    response = client.get(f"{PROBE}/p2", headers=customer)
    assert response.json()["error"]["code"] == "feature_not_available"
    assert response.json()["error"]["message"] == "هذه الميزة غير متاحة."  # customer's saved language is Arabic


def test_case06_release_control_is_super_admin_only(client, customer):
    client_admin = login(client, "client-admin@example.com")
    for headers in (customer, client_admin):
        assert client.get(f"{ADMIN}/state", headers=headers).status_code == 403
        assert client.get(f"{ADMIN}/history", headers=headers).status_code == 403
        response = client.post(
            f"{ADMIN}/releases", json={"note": "sneaky", "phases": {"phase2": True}}, headers=headers
        )
        assert response.status_code == 403
    assert client.get(f"{ADMIN}/state").status_code == 401
    assert probe(client, customer, "p2") == 404


def test_case06_preview_header_is_ignored_for_non_super_admin(client, customer, owner, release):
    scheduled = release(phases={"phase2": True}, activate_at=(datetime.now(UTC) + timedelta(days=1)).isoformat())
    preview = {"X-Release-Preview": scheduled.json()["id"]}
    assert probe(client, {**customer, **preview}, "p2") == 404
    assert probe(client, preview, "p2") == 404
    # The Super Admin sees the app as it will be, without changing it for anyone else.
    assert probe(client, {**owner, **preview}, "p2") == 200
    assert client.get(FEATURES, headers={**owner, **preview}).json()["preview"] is True
    assert probe(client, owner, "p2") == 404


def test_case10_case11_users_survive_phase_deactivation(client, db, release):
    before = db.scalar(select(func.count()).select_from(User))
    release(phases={"phase2": True, "phase3": True})
    release(phases={"phase2": False, "phase3": False})
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(User)) == before
    assert client.get("/api/v1/users/me", headers=login(client, "customer@example.com")).status_code == 200


def test_case12_rollback_restores_an_earlier_release(client, customer, owner, release):
    initial = client.get(f"{ADMIN}/releases", headers=owner).json()[-1]
    release(phases={"phase2": True})
    release(features={"phase1.eyewear": False})
    assert [probe(client, customer, p) for p in ("p1-enh", "p2")] == [404, 200]

    response = client.post(
        f"{ADMIN}/releases/{initial['id']}/rollback", json={"note": "back to launch state"}, headers=owner
    )
    assert response.status_code == 201
    assert response.json()["restored_from_id"] == initial["id"]
    assert [probe(client, customer, p) for p in ("p1-enh", "p2")] == [200, 404]

    history = client.get(f"{ADMIN}/history", headers=owner).json()
    assert [h["action"] for h in history] == ["rolled_back", "activated", "activated", "seeded"]
    assert history[0]["detail"]["disabled"]  # records exactly what the rollback switched off
    statuses = [r["status"] for r in client.get(f"{ADMIN}/releases", headers=owner).json()]
    assert statuses == ["active", "superseded", "superseded", "superseded"]


def test_individual_feature_can_be_switched_without_touching_its_phase(client, customer, release):
    assert release(features={"phase1.eyewear": False}).status_code == 201
    assert [probe(client, customer, p) for p in ("p1", "p1-enh")] == [200, 404]
    assert "phase1.eyewear" not in client.get(FEATURES, headers=customer).json()["features"]


def test_cannot_disable_a_feature_that_an_enabled_feature_needs(client, customer, release):
    release(phases={"phase2": True})
    # Excel row 23: makeup audit requires completed seasonal colour analysis.
    response = release(features={"phase1.seasonal_color": False})
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "dependency_violation"
    assert {"feature": "phase2.makeup_audit", "requires": "phase1.seasonal_color"}.items() <= error["detail"][
        "violations"
    ][0].items()
    assert probe(client, customer, "p2-makeup") == 200  # nothing changed
    # Switching both off together is allowed.
    assert release(features={"phase1.seasonal_color": False, "phase2.makeup_audit": False}).status_code == 201


def test_cannot_enable_phase3_without_what_it_builds_on(client, release):
    response = release(phases={"phase3": True})
    assert response.status_code == 409
    needed = {v["requires"] for v in response.json()["error"]["detail"]["violations"]}
    assert needed == {"phase2.booking", "phase2.stylist_discovery"}


def test_cannot_disable_phase1_while_phase2_is_on(client, release):
    release(phases={"phase2": True})
    assert release(phases={"phase1": False}).status_code == 409


def test_validate_is_a_dry_run(client, owner, customer):
    response = client.post(f"{ADMIN}/releases/validate", json={"phases": {"phase2": True}}, headers=owner)
    body = response.json()
    assert body["violations"] == [] and len(body["would_enable"]) == 24 and body["would_disable"] == []
    assert probe(client, customer, "p2") == 404


def test_release_requires_a_note_known_keys_and_a_real_change(client, owner, release):
    assert client.post(f"{ADMIN}/releases", json={"phases": {"phase2": True}}, headers=owner).status_code == 422
    assert release(phases={"phase9": True}).json()["error"]["code"] == "unknown_key"
    assert release(phases={"phase1": True}).json()["error"]["code"] == "no_changes"


def test_scheduled_release_activates_when_due(client, customer, db, release):
    due = datetime.now(UTC) + timedelta(hours=1)
    response = release(phases={"phase2": True}, activate_at=due.isoformat())
    assert response.status_code == 201 and response.json()["status"] == "scheduled"
    assert probe(client, customer, "p2") == 404

    assert service.apply_due(db, now=due - timedelta(minutes=1)) == 0
    assert service.apply_due(db, now=due + timedelta(minutes=1)) == 1
    db.commit()
    assert probe(client, customer, "p2") == 200


def test_scheduled_release_applies_on_the_next_request_even_without_a_worker(client, customer, db, release):
    scheduled = release(phases={"phase2": True}, activate_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat())
    db.execute(
        update(ReleaseConfiguration)
        .where(ReleaseConfiguration.version == scheduled.json()["version"])
        .values(activate_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    db.commit()
    assert probe(client, customer, "p2") == 200


def test_scheduled_release_that_no_longer_validates_fails_safely(client, customer, db, release):
    release(phases={"phase2": True})
    due = datetime.now(UTC) + timedelta(hours=1)
    scheduled = release(features={"phase2.makeup_audit": False, "phase1.seasonal_color": False}, activate_at=due.isoformat())
    assert scheduled.status_code == 201
    # Before it is due, someone turns makeup audit's switch back into play differently:
    release(features={"phase2.testimonials": False})
    db.execute(
        update(ReleaseConfiguration)
        .where(ReleaseConfiguration.version == scheduled.json()["version"])
        .values(changes={"phases": {}, "features": {"phase1.seasonal_color": False}})
    )
    db.commit()
    assert service.apply_due(db, now=due + timedelta(minutes=1)) == 0
    db.commit()
    failed = db.scalar(select(ReleaseConfiguration).where(ReleaseConfiguration.version == scheduled.json()["version"]))
    assert failed.status == "failed"
    assert db.scalar(select(ReleaseHistory).where(ReleaseHistory.action == "failed")) is not None
    assert probe(client, customer, "p2-makeup") == 200  # active release untouched


def test_scheduled_release_can_be_cancelled(client, owner, db, release):
    due = datetime.now(UTC) + timedelta(hours=1)
    scheduled = release(phases={"phase2": True}, activate_at=due.isoformat()).json()
    assert client.post(f"{ADMIN}/releases/{scheduled['id']}/cancel", headers=owner).json()["status"] == "cancelled"
    assert service.apply_due(db, now=due + timedelta(hours=1)) == 0
    assert client.post(f"{ADMIN}/releases/{scheduled['id']}/cancel", headers=owner).status_code == 409


def test_schedule_must_be_in_the_future(release):
    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    assert release(phases={"phase2": True}, activate_at=past).json()["error"]["code"] == "invalid_schedule"


def test_database_allows_only_one_active_release(db):
    active = service.active_release(db)
    db.add(ReleaseConfiguration(status="active", note="second active", snapshot=active.snapshot))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_state_lists_every_excel_feature_with_its_source_row(client, owner):
    state = client.get(f"{ADMIN}/state", headers=owner).json()
    assert [p["enabled"] for p in state["phases"]] == [True, False, False]
    assert [f["source_row"] for f in state["features"]] == list(range(1, 53))
    makeup = next(f for f in state["features"] if f["key"] == "phase2.makeup_audit")
    assert makeup["switch_on"] is True and makeup["available"] is False
    assert "phase1.seasonal_color" in makeup["requires"]


def test_seed_is_idempotent(db):
    from app.modules.phase_management.seed import seed

    seed(db)
    db.commit()
    assert db.scalar(select(func.count()).select_from(ReleaseConfiguration)) == 1
