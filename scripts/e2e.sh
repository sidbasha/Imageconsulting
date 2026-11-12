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
WORK="$(mktemp -d)"
export IC_STORAGE_DIR="$WORK/uploads"
export E2E_PHOTO_DIR="$WORK/photos"

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

# Test photos: a real portrait (bundled with scikit-image) and a blurred copy.
python - <<'PY'
import os
import cv2
from skimage import data
os.makedirs(os.environ["E2E_PHOTO_DIR"])
portrait = cv2.cvtColor(cv2.resize(data.astronaut()[0:400, 60:460], (600, 600), interpolation=cv2.INTER_CUBIC), cv2.COLOR_RGB2BGR)
cv2.imwrite(os.environ["E2E_PHOTO_DIR"] + "/good.jpg", portrait, [cv2.IMWRITE_JPEG_QUALITY, 92])
cv2.imwrite(os.environ["E2E_PHOTO_DIR"] + "/blurry.jpg", cv2.GaussianBlur(portrait, (0, 0), 9))
PY
# Colour headshot for photo analysis (attribution in backend/app/tests/fixtures/ATTRIBUTION.md).
cp app/tests/fixtures/face_colour.jpg "$E2E_PHOTO_DIR/colour.jpg"
python -m app.cli fetch-models

uvicorn app.main:app --port "$PORT" --log-level warning &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true; rm -rf "$WORK"' EXIT
for _ in $(seq 1 40); do
  curl -fs "http://localhost:$PORT/health" >/dev/null && break
  sleep 0.25
done

cd "$ROOT/mobile"
E2E_API_URL="http://localhost:$PORT" npx jest --config jest.e2e.config.js
