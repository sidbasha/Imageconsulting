"""Admin Dashboard -> Settings -> Phase Management. Super Admin only."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.core.errors import AppError
from app.database.session import get_db
from app.modules.auth.models import User
from app.modules.phase_management import service
from app.modules.phase_management.models import ReleaseConfiguration, ReleaseHistory
from app.modules.phase_management.schemas import ChangesIn, HistoryOut, ReleaseIn, ReleaseOut, RollbackIn

router = APIRouter(prefix="/admin/phase-management", tags=["phase-management"])
can_view = require_permission("release.view")
can_manage = require_permission("release.manage")


@router.get("/state")
def state(db: Session = Depends(get_db), _: User = Depends(can_view)) -> dict:
    """Every phase and feature with its switch and whether it is currently available."""
    release, snapshot = service.current_snapshot(db)
    return service.describe_state(db, release, snapshot)


@router.post("/releases/validate")
def validate(body: ChangesIn, db: Session = Depends(get_db), _: User = Depends(can_manage)) -> dict:
    """Dry run: what would change and which dependencies would break."""
    return service.validate_changes(db, body.as_changes())


@router.post("/releases", response_model=ReleaseOut, status_code=status.HTTP_201_CREATED)
def create_release(
    body: ReleaseIn, db: Session = Depends(get_db), actor: User = Depends(can_manage)
) -> ReleaseConfiguration:
    """Enable or disable phases and features, now or at `activate_at`."""
    return service.create_release(db, actor, body.as_changes(), body.note, body.activate_at)


@router.get("/releases", response_model=list[ReleaseOut])
def list_releases(
    limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), _: User = Depends(can_view)
) -> list[ReleaseConfiguration]:
    return list(
        db.scalars(select(ReleaseConfiguration).order_by(ReleaseConfiguration.version.desc()).limit(limit))
    )


@router.get("/releases/{release_id}", response_model=ReleaseOut)
def get_release(
    release_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(can_view)
) -> ReleaseConfiguration:
    release = db.get(ReleaseConfiguration, release_id)
    if release is None:
        raise AppError(404, "not_found")
    return release


@router.post("/releases/{release_id}/rollback", response_model=ReleaseOut, status_code=status.HTTP_201_CREATED)
def rollback(
    release_id: uuid.UUID, body: RollbackIn, db: Session = Depends(get_db), actor: User = Depends(can_manage)
) -> ReleaseConfiguration:
    """Restore the state of an earlier release as a new release."""
    return service.rollback(db, actor, release_id, body.note)


@router.post("/releases/{release_id}/cancel", response_model=ReleaseOut)
def cancel(
    release_id: uuid.UUID, db: Session = Depends(get_db), actor: User = Depends(can_manage)
) -> ReleaseConfiguration:
    return service.cancel(db, actor, release_id)


@router.get("/history", response_model=list[HistoryOut])
def history(
    limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), _: User = Depends(can_view)
) -> list[ReleaseHistory]:
    return list(db.scalars(select(ReleaseHistory).order_by(ReleaseHistory.created_at.desc()).limit(limit)))
