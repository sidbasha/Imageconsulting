# Image Consulting Application

One product, three release phases, controlled from a Super Admin panel. English and Arabic.
See `STATUS.md` for exactly what exists today and what does not.

## Layout

```
backend/   FastAPI modular monolith (Python), PostgreSQL, Alembic
docs/      Requirements Traceability Matrix and its generator
mobile/    React Native app with android/ and ios/ (foundation; see mobile/README.md)
scripts/   e2e.sh: API + mobile client end-to-end check
admin/     React admin panel (see admin/README.md)
```

## Run locally

```bash
docker compose up --build            # API on http://localhost:8000, docs at /docs
docker compose exec api python -m app.cli create-superadmin --email you@example.com --name "You"
```

Without Docker (PostgreSQL 16 running, database and user created):

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.cli fetch-models       # photo-analysis models (MediaPipe), checksum-verified
python -m app.cli seed               # roles, 52 feature keys, release 1 = Phase 1 only, draft catalogue
python -m app.cli create-superadmin --email you@example.com --name "You"
uvicorn app.main:app --reload
```

Tests need a PostgreSQL database (default `ic_test`, override with `IC_TEST_DATABASE_URL`):

```bash
cd backend && python -m pytest
```

## Releasing a phase

All calls need a Super Admin access token (`POST /api/v1/auth/login`).

```bash
BASE=http://localhost:8000/api/v1/admin/phase-management

# What is on, what is off, and what each feature depends on
curl -H "Authorization: Bearer $TOKEN" $BASE/state

# Dry run
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"phases": {"phase2": true}}' $BASE/releases/validate

# Release Phase 2 now (add "activate_at": "2027-01-15T06:00:00+04:00" to schedule it)
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"phases": {"phase2": true}, "note": "Phase 2 delivered to client"}' $BASE/releases

# Switch one feature
curl -X POST ... -d '{"features": {"phase1.eyewear": false}, "note": "Pending client decision"}' $BASE/releases

# History, and rollback to an earlier release
curl -H "Authorization: Bearer $TOKEN" $BASE/history
curl -X POST ... -d '{"note": "Reverting"}' $BASE/releases/<release id>/rollback

# See the app as a stored or scheduled release would show it (Super Admin only)
curl -H "Authorization: Bearer $TOKEN" -H "X-Release-Preview: <release id>" \
     http://localhost:8000/api/v1/config/features
```

Scheduled releases activate on the next API request after they fall due. Also run
`python -m app.cli apply-due` every minute (cron now, Celery beat later) so a schedule holds
with no traffic, and `python -m app.cli renew-subscriptions` daily.

## Policy settings

Values the client has not decided yet (minimum age, women-only, violation thresholds, ranking
weights, cancellation window, prices of featured placement...) are settings, not code:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/settings
curl -X PUT ... -d '{"value": 16}' http://localhost:8000/api/v1/admin/settings/eligibility.min_age
```

## Sandboxes

Payments and UAE Pass run against sandbox providers outside production. In development the
app shows a "complete test payment" button; the backend refuses to start them when
`IC_ENV=production`.

## Adding a module behind a feature

```python
from fastapi import APIRouter, Depends
from app.modules.feature_flags.guard import require_feature

router = APIRouter(prefix="/bookings", dependencies=[Depends(require_feature("phase2.booking"))])
```

Feature keys live in `backend/app/modules/phase_management/catalog.py`, each traced to a row
of the client's Feature List. Regenerate the RTM after changing the catalog:

```bash
python docs/build_rtm.py "<path to Image_Consulting_Feature_List_v.1.0.xlsx>"
```
