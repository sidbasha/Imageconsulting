import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.core import keep_alive


def _server(status: int):
    hits = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            hits.set()
            self.send_response(status)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}/health", hits


def test_ping_reports_success_and_failure():
    ok, ok_url, _ = _server(200)
    bad, bad_url, _ = _server(503)
    try:
        assert keep_alive.ping(ok_url) is True
        assert keep_alive.ping(bad_url) is False
        assert keep_alive.ping("http://127.0.0.1:9/health", timeout=2) is False
    finally:
        ok.shutdown()
        bad.shutdown()


def test_loop_pings_repeatedly_until_stopped():
    server, url, hits = _server(200)
    try:
        stop = keep_alive.start(url, minutes=0.01)  # every 0.6 s
        assert hits.wait(5)
        stop.set()
    finally:
        server.shutdown()


def test_app_starts_keep_alive_only_when_configured(monkeypatch):
    from app.main import create_app

    started = []
    monkeypatch.setattr(keep_alive, "start", lambda url, minutes: started.append((url, minutes)) or threading.Event())

    with TestClient(create_app()):
        pass
    assert started == []

    monkeypatch.setenv("IC_KEEP_ALIVE_URL", "https://api.example.com/health")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()):
            pass
    finally:
        get_settings.cache_clear()
    assert started == [("https://api.example.com/health", 10)]


def test_auto_uses_render_external_url(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    assert keep_alive.resolve("auto") == ""
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://ic-api.onrender.com/")
    assert keep_alive.resolve("auto") == "https://ic-api.onrender.com/health"
    assert keep_alive.resolve(" https://x.example/health ") == "https://x.example/health"
    assert keep_alive.resolve("") == ""
