"""Idempotent seed of roles, permissions, the feature catalog and release 1."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.assessments.service import seed_content
from app.modules.commerce.service import seed as commerce_seed
from app.modules.consultations.service import seed as templates_seed
from app.modules.rewards.service import seed as rewards_seed
from app.modules.platform.service import seed as platform_seed
from app.modules.auth.models import Permission, Role
from app.modules.phase_management import catalog, service
from app.modules.phase_management.models import (
    ApplicationPhase,
    FeatureDependency,
    FeatureFlag,
    FeatureModule,
    ReleaseConfiguration,
)


def _by_key(db: Session, model) -> dict:
    return {row.key: row for row in db.scalars(select(model))}


def seed(db: Session) -> None:
    roles = _by_key(db, Role)
    for key, name in catalog.ROLES:
        if key not in roles:
            roles[key] = Role(key=key, name=name)
            db.add(roles[key])
    permissions = _by_key(db, Permission)
    for key, role_keys in catalog.PERMISSIONS.items():
        if key not in permissions:
            permissions[key] = Permission(key=key)
            db.add(permissions[key])
        for role_key in role_keys:
            if permissions[key] not in roles[role_key].permissions:
                roles[role_key].permissions.append(permissions[key])

    phases = _by_key(db, ApplicationPhase)
    for key, name, order in catalog.PHASES:
        if key not in phases:
            phases[key] = ApplicationPhase(key=key, name=name, sort_order=order)
            db.add(phases[key])
    modules = _by_key(db, FeatureModule)
    for key, name in catalog.MODULES:
        if key not in modules:
            modules[key] = FeatureModule(key=key, name=name)
            db.add(modules[key])
    db.flush()

    flags = _by_key(db, FeatureFlag)
    for row, key, name, module, phase, label, enhancement in catalog.FEATURES:
        if key not in flags:
            # Phase is set on first seed only: later reassignments made in the
            # admin panel must survive a re-seed.
            flags[key] = FeatureFlag(
                key=key,
                name=name,
                phase_id=phases[phase].id,
                module_id=modules[module].id,
                source_row=row,
                source_phase_label=label,
                is_enhancement=enhancement,
            )
            db.add(flags[key])
    db.flush()

    existing = {(d.feature_id, d.requires_feature_id) for d in db.scalars(select(FeatureDependency))}
    for feature, requires, basis, reason in catalog.DEPENDENCIES:
        pair = (flags[feature].id, flags[requires].id)
        if pair not in existing:
            db.add(FeatureDependency(feature_id=pair[0], requires_feature_id=pair[1], basis=basis, reason=reason))
    db.flush()

    has_active = db.execute(
        select(ReleaseConfiguration.id).where(ReleaseConfiguration.status == "active")
    ).first()
    if not has_active:
        snapshot = service.reconcile(
            db, {"phases": dict(catalog.INITIAL_PHASE_STATE), "features": {}}, default_enabled=True
        )
        problems = service.violations(db, snapshot)
        if problems:
            raise RuntimeError(f"Initial release violates dependencies: {problems}")
        release = ReleaseConfiguration(note="Initial release: Phase 1 only", changes=None)
        service._activate(db, release, snapshot, None, None, "seeded", datetime.now(UTC))
    db.flush()
    seed_content(db)
    platform_seed(db)
    commerce_seed(db)
    rewards_seed(db)
    templates_seed(db)
