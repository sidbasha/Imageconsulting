"""Applies app/release_plan.py through the release service (developers only)."""

import importlib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.phase_management import catalog, service
from app.modules.phase_management.models import FeatureFlag, ReleaseConfiguration


def load_plan() -> dict:
    from app import release_plan

    importlib.reload(release_plan)  # always the file as it is now
    phases = {k: bool(v) for k, v in release_plan.PHASES.items()}
    features = {k: bool(v) for k, v in release_plan.FEATURES.items()}
    known_phases = {key for key, *_ in catalog.PHASES}
    known_features = {row[1] for row in catalog.FEATURES}
    unknown = sorted((phases.keys() - known_phases) | (features.keys() - known_features))
    if unknown:
        raise SystemExit(f"release_plan.py names keys that do not exist: {', '.join(unknown)}")
    return {"phases": phases, "features": features}


def changes_from_plan(db: Session) -> dict:
    """The full desired state: every feature on unless the plan switches it off."""
    plan = load_plan()
    all_features = [f.key for f in db.scalars(select(FeatureFlag))]
    return {"phases": plan["phases"], "features": {k: plan["features"].get(k, True) for k in all_features}}


def check(db: Session) -> dict:
    return service.validate_changes(db, changes_from_plan(db))


def apply(db: Session, note: str, activate_at: datetime | None = None) -> ReleaseConfiguration | None:
    """Applies the plan. Returns None when it is already live."""
    try:
        return service.create_release(db, None, changes_from_plan(db), note, activate_at)
    except AppError as exc:
        if exc.code == "no_changes":
            return None
        raise


def status(db: Session) -> dict:
    release, snapshot = service.current_snapshot(db)
    state = service.describe_state(db, release, snapshot)
    return {
        "version": release.version,
        "phases": {p["key"]: p["enabled"] for p in state["phases"]},
        "live": sorted(f["key"] for f in state["features"] if f["available"]),
        "hidden": sorted(f["key"] for f in state["features"] if not f["available"]),
    }


def history(db: Session, limit: int = 20) -> list[dict]:
    releases = db.scalars(select(ReleaseConfiguration).order_by(ReleaseConfiguration.version.desc()).limit(limit))
    return [{"version": r.version, "status": r.status, "note": r.note, "activated_at": r.activated_at,
             "activate_at": r.activate_at, "id": r.id} for r in releases]


def by_version(db: Session, version: int) -> ReleaseConfiguration:
    release = db.execute(select(ReleaseConfiguration).where(ReleaseConfiguration.version == version)).scalar_one_or_none()
    if release is None:
        raise SystemExit(f"No release v{version}.")
    return release

