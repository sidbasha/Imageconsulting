"""Application errors carry a stable code; the message is localized on output."""

import json
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config.settings import get_settings

_LOCALES = Path(__file__).resolve().parent.parent / "localization"
_MESSAGES = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in _LOCALES.glob("*.json")}


class AppError(Exception):
    def __init__(self, status: int, code: str, detail: object | None = None):
        self.status, self.code, self.detail = status, code, detail


def pick_language(request: Request) -> str:
    settings = get_settings()
    explicit = getattr(request.state, "language", None)
    if explicit in settings.supported_languages:
        return explicit
    for part in request.headers.get("accept-language", "").split(","):
        tag = part.split(";")[0].strip().lower()[:2]
        if tag in settings.supported_languages:
            return tag
    return settings.default_language


def translate(code: str, language: str) -> str:
    return _MESSAGES.get(language, {}).get(code) or _MESSAGES["en"].get(code, code)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    language = pick_language(request)
    body = {"error": {"code": exc.code, "message": translate(exc.code, language)}}
    if exc.detail is not None:
        body["error"]["detail"] = exc.detail
    return JSONResponse(body, status_code=exc.status, headers={"Content-Language": language})
