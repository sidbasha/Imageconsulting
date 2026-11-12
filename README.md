# Image Consulting Application

One product, three release phases, switched by developers in the codebase. English and Arabic.
See `STATUS.md` for exactly what exists today and what does not.

## Layout

```
backend/   FastAPI modular monolith (Python), PostgreSQL, Alembic
docs/      Requirements Traceability Matrix and its generator
mobile/    React Native app with android/ and ios/; staff see an Admin tab (see mobile/README.md)
scripts/   e2e.sh: API + mobile client end-to-end check
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

## Releasing a phase (developers only)

There is no screen and no API for this, on purpose. Phases and features are switched in
`backend/app/release_plan.py`:

```python
PHASES = {"phase1": True, "phase2": True, "phase3": False}
FEATURES = {"phase1.eyewear": False}   # optional: hide one feature inside a phase that is on
```

Then, from `backend/`:

```bash
python -m app.cli release check                     # dry run: what turns on/off, dependency problems
python -m app.cli release apply --note "Phase 2 for the client"
python -m app.cli release apply --note "Launch" --at 2027-01-15T06:00:00+04:00   # scheduled
python -m app.cli release status                    # what is live now
python -m app.cli release history
python -m app.cli release rollback 3 --note "Back to v3"
python -m app.cli release cancel 5                  # a scheduled release
```

Deploys run `release apply` at container start, so committing a change to the file and
deploying is enough. A release that would leave an enabled feature without one it depends on is
refused with the reason. Switching something off hides it; data is kept. Run
`python -m app.cli apply-due` every minute (cron) so a scheduled release activates on time, and
`python -m app.cli renew-subscriptions` daily.

## Deploy the API to Render (free demo)

`render.yaml` describes one free Docker web service in Ohio, next to the Neon database.
In the Render dashboard: **New → Blueprint**, connect this GitHub repo and branch, then paste
the Neon pooled URL into `IC_DATABASE_URL` and the direct URL into `IC_MIGRATION_DATABASE_URL`.
Each start runs migrations, the seed and `release apply`. The free instance has 512 MB RAM and
a disk that is wiped on restart, so files go to Neon Object Storage: set `IC_STORAGE_BACKEND=s3`,
`IC_S3_BUCKET` and the four `AWS_*` values from `backend/.env` in the service's Environment. Point the app at it with `PRODUCTION_API_URL` in `mobile/src/config.ts`.

## Demo hosting that does not sleep

Free hosts (e.g. Render's free web service) stop the API after ~15 minutes without traffic.
Two pings keep a demo awake:

1. **Self-ping:** set `IC_KEEP_ALIVE_URL=https://<api-host>/health` on the host (on Render,
   `auto` uses the service's own address; `render.yaml` sets it). The API
   requests its own public health check every `IC_KEEP_ALIVE_MINUTES` (default 10).
2. **Backup cron:** `.github/workflows/keep-alive.yml` pings the same URL every 10 minutes
   from GitHub Actions, which wakes the API if it ever did sleep. Set the repository
   variable `KEEP_ALIVE_URL` (Settings → Secrets and variables → Actions → Variables).
   Schedules run only from the default branch.

`/health` does not query the database, so a serverless database (Neon) can still sleep
between real requests and keep within its free compute hours. Leave both unset on paid hosting.

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
