FROM python:3.13-slim
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Shared libraries needed even on a headless server: OpenCV wants libGL and GLib;
# MediaPipe's libmediapipe.so links libEGL and libGLESv2 (it fails to load without them).
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libegl1 libgles2 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m app.cli fetch-models
RUN useradd --system app && chown -R app /srv
USER app
# Hosts such as Render set PORT; 8000 otherwise.
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.cli seed && python -m app.cli release apply --note \"Deploy: app/release_plan.py\" && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
