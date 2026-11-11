#!/usr/bin/env bash
# End-to-end check: starts the API on a scratch database and runs the mobile
# app's client against it over real HTTP.
#
# Needs PostgreSQL reachable with a role that can create databases:
#   E2E_PG_URL=postgresql://ic:ic@localhost:5432  (default)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PG="${E2E_PG_URL:-postgresql://ic:ic@localhost:5432}"
DB="ic_e2e"
PORT="${E2E_PORT:-8011}"
export E2E_ADMIN_EMAIL="owner-e2e@example.com"
export E2E_ADMIN_PASSWORD="owner-e2e-password"
export IC_ENV=testing
export IC_DATABASE_URL="${PG/postgresql:/postgresql+psycopg:}/$DB"

psql "$PG/postgres" -qc "DROP DATABASE IF EXISTS $DB" -c "CREATE DATABASE $DB"

cd "$ROOT/backend"
alembic upgrade head
python -m app.cli seed
python - <<'PY'
import os
from app.database import models  # noqa: F401
from app.database.session import SessionLocal
from app.modules.auth.service import create_user
with SessionLocal() as db:
    create_user(db, email=os.environ["E2E_ADMIN_EMAIL"], password=os.environ["E2E_ADMIN_PASSWORD"],
                full_name="E2E Owner", role_key="super_admin")
    db.commit()
PY

uvicorn app.main:app --port "$PORT" --log-level warning &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT
for _ in $(seq 1 40); do
  curl -fs "http://localhost:$PORT/health" >/dev/null && break
  sleep 0.25
done

cd "$ROOT/mobile"
E2E_API_URL="http://localhost:$PORT" npx jest --config jest.e2e.config.js
