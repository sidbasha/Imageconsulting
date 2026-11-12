"""Release control.

Release state has one source of truth: the snapshot of the single active
ReleaseConfiguration. A snapshot looks like

    {"phases":   {"phase1": true, "phase2": false, ...},
     "features": {"phase1.face_shape": {"enabled": true, "phase": "phase1"}, ...}}

A feature is available when its own switch AND its phase are on. Nothing here
touches business data, so disabling a phase can never delete anything.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.auth.models import User
from app.modules.phase_management.models import (
    ApplicationPhase,
    FeatureDependency,
    FeatureFlag,
    ReleaseConfiguration,
    ReleaseHistory,
)

Snapshot = dict
Changes = dict


def effective_keys(snapshot: Snapshot) -> set[str]:
    phases = snapshot["phases"]
    return {
        key for key, f in snapshot["features"].items() if f["enabled"] and phases.get(f["phase"], False)
    }


def reconcile(db: Session, snapshot: Snapshot, *, default_enabled: bool) -> Snapshot:
    """Aligns a snapshot with the current catalog: picks up phase reassignments,
    adds features created since (with the given default), drops removed ones."""
    phases = {p.key: bool(snapshot["phases"].get(p.key, False)) for p in db.scalars(select(ApplicationPhase))}
    features = {}
    for flag in db.scalars(select(FeatureFlag)):
        previous = snapshot["features"].get(flag.key)
        enabled = previous["enabled"] if previous else default_enabled
        features[flag.key] = {"enabled": enabled, "phase": flag.phase.key}
    return {"phases": phases, "features": features}


def resolve(db: Session, base: Snapshot, changes: Changes) -> Snapshot:
    """Applies a change set to a base snapshot."""
    snapshot = reconcile(db, base, default_enabled=False)
    unknown = [k for k in changes.get("phases", {}) if k not in snapshot["phases"]]
    unknown += [k for k in changes.get("features", {}) if k not in snapshot["features"]]
    if unknown:
        raise AppError(422, "unknown_key", {"keys": sorted(unknown)})
    for key, enabled in changes.get("phases", {}).items():
        snapshot["phases"][key] = bool(enabled)
    for key, enabled in changes.get("features", {}).items():
        snapshot["features"][key]["enabled"] = bool(enabled)
    return snapshot


def violations(db: Session, snapshot: Snapshot) -> list[dict]:
    """An available feature must not depend on an unavailable one."""
    on = effective_keys(snapshot)
    found = []
    for dep in db.scalars(select(FeatureDependency)):
        if dep.feature.key in on and dep.requires.key not in on:
            found.append({"feature": dep.feature.key, "requires": dep.requires.key, "reason": dep.reason})
    return sorted(found, key=lambda v: (v["feature"], v["requires"]))


def active_release(db: Session, *, lock: bool = False) -> ReleaseConfiguration:
    query = select(ReleaseConfiguration).where(ReleaseConfiguration.status == "active")
    if lock:
        query = query.with_for_update()
    return db.execute(query).scalar_one()


def _record(db, release, action, actor, previous=None, detail=None) -> None:
    db.add(
        ReleaseHistory(
            release_id=release.id,
            previous_release_id=previous.id if previous else None,
            action=action,
            actor_id=actor.id if actor else None,
            detail=detail,
        )
    )


def _activate(db, release, snapshot, previous, actor, action, now) -> None:
    """Swap the active release inside the caller's transaction. The partial
    unique index allows one active row, so the old one is demoted first."""
    if previous is not None:
        previous.status = "superseded"
        db.flush()
    release.snapshot = snapshot
    release.status = "active"
    release.activated_at = now
    db.add(release)
    db.flush()
    before = effective_keys(previous.snapshot) if previous else set()
    after = effective_keys(snapshot)
    _record(
        db,
        release,
        action,
        actor,
        previous,
        {"enabled": sorted(after - before), "disabled": sorted(before - after), "phases": snapshot["phases"]},
    )


def validate_changes(db: Session, changes: Changes) -> dict:
    """Dry run against the active release."""
    current = active_release(db)
    snapshot = resolve(db, current.snapshot, changes)
    before, after = effective_keys(current.snapshot), effective_keys(snapshot)
    return {
        "violations": violations(db, snapshot),
        "would_enable": sorted(after - before),
        "would_disable": sorted(before - after),
    }


def create_release(
    db: Session,
    actor: User | None,
    changes: Changes,
    note: str,
    activate_at: datetime | None = None,
    now: datetime | None = None,
) -> ReleaseConfiguration:
    now = now or datetime.now(UTC)
    current = active_release(db, lock=True)
    snapshot = resolve(db, current.snapshot, changes)
    problems = violations(db, snapshot)
    if problems:
        raise AppError(409, "dependency_violation", {"violations": problems})
    if snapshot == reconcile(db, current.snapshot, default_enabled=False):
        raise AppError(409, "no_changes")

    release = ReleaseConfiguration(note=note, changes=changes, created_by_id=actor.id if actor else None)
    if activate_at is not None:
        if activate_at <= now:
            raise AppError(422, "invalid_schedule")
        release.status, release.activate_at = "scheduled", activate_at
        db.add(release)
        db.flush()
        _record(db, release, "scheduled", actor, current, {"activate_at": activate_at.isoformat()})
    else:
        _activate(db, release, snapshot, current, actor, "activated", now)
    return release


def apply_due(db: Session, now: datetime | None = None) -> int:
    """Activates scheduled releases whose time has come. Each is resolved against
    whatever is active at that moment and validated again; if it no longer
    validates it is marked failed and the active release is left untouched."""
    now = now or datetime.now(UTC)
    due = db.scalars(
        select(ReleaseConfiguration)
        .where(ReleaseConfiguration.status == "scheduled", ReleaseConfiguration.activate_at <= now)
        .order_by(ReleaseConfiguration.activate_at, ReleaseConfiguration.version)
        .with_for_update(skip_locked=True)
    ).all()
    applied = 0
    for release in due:
        current = active_release(db, lock=True)
        try:
            snapshot = resolve(db, current.snapshot, release.changes or {})
            problems = violations(db, snapshot)
        except AppError as exc:
            snapshot, problems = None, [{"error": exc.code, "detail": exc.detail}]
        if problems:
            release.status = "failed"
            _record(db, release, "failed", None, current, {"violations": problems})
            continue
        _activate(db, release, snapshot, current, None, "activated", now)
        applied += 1
    db.flush()
    return applied


def rollback(db: Session, actor: User | None, target_id: uuid.UUID, note: str) -> ReleaseConfiguration:
    """Restores the state of an earlier release as a NEW release, so history
    stays linear. Features added to the catalog since then come back disabled."""
    target = db.get(ReleaseConfiguration, target_id)
    if target is None:
        raise AppError(404, "not_found")
    if target.snapshot is None or target.status not in ("superseded", "active"):
        raise AppError(409, "release_not_restorable")
    current = active_release(db, lock=True)
    snapshot = reconcile(db, target.snapshot, default_enabled=False)
    problems = violations(db, snapshot)
    if problems:
        raise AppError(409, "dependency_violation", {"violations": problems})
    if snapshot == reconcile(db, current.snapshot, default_enabled=False):
        raise AppError(409, "no_changes")
    release = ReleaseConfiguration(
        note=note, restored_from_id=target.id, created_by_id=actor.id if actor else None
    )
    _activate(db, release, snapshot, current, actor, "rolled_back", datetime.now(UTC))
    return release


def cancel(db: Session, actor: User | None, release_id: uuid.UUID) -> ReleaseConfiguration:
    release = db.get(ReleaseConfiguration, release_id, with_for_update=True)
    if release is None:
        raise AppError(404, "not_found")
    if release.status != "scheduled":
        raise AppError(409, "release_not_scheduled")
    release.status = "cancelled"
    _record(db, release, "cancelled", actor)
    db.flush()
    return release


def current_snapshot(db: Session) -> tuple[ReleaseConfiguration, Snapshot]:
    """What the API enforces right now. Due scheduled releases are applied here
    as well as by the worker, so a schedule holds even if the worker is down.
    Costs two indexed queries per request; a Redis cache keyed on the active
    version is the planned optimisation once load requires it."""
    apply_due(db)
    release = active_release(db)
    return release, release.snapshot


def is_enabled(db: Session, key: str) -> bool:
    """For service-to-service checks inside business workflows."""
    return key in effective_keys(current_snapshot(db)[1])


def describe_state(db: Session, release: ReleaseConfiguration, snapshot: Snapshot) -> dict:
    on = effective_keys(snapshot)
    requires: dict[str, list[str]] = {}
    for dep in db.scalars(select(FeatureDependency)):
        requires.setdefault(dep.feature.key, []).append(dep.requires.key)
    phases = db.scalars(select(ApplicationPhase).order_by(ApplicationPhase.sort_order)).all()
    flags = db.scalars(select(FeatureFlag).order_by(FeatureFlag.source_row, FeatureFlag.key)).all()
    return {
        "release_id": release.id,
        "release_version": release.version,
        "phases": [{"key": p.key, "name": p.name, "enabled": snapshot["phases"].get(p.key, False)} for p in phases],
        "features": [
            {
                "key": f.key,
                "name": f.name,
                "phase": f.phase.key,
                "module": f.module.key,
                "switch_on": snapshot["features"].get(f.key, {}).get("enabled", False),
                "available": f.key in on,
                "is_enhancement": f.is_enhancement,
                "source_row": f.source_row,
                "source_phase_label": f.source_phase_label,
                "requires": sorted(requires.get(f.key, [])),
            }
            for f in flags
        ],
    }
