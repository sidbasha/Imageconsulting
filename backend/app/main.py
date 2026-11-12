from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.errors import AppError, app_error_handler
from app.modules.ai_analysis.router import admin_tryon, catalogue as tryon_catalogue, colour_types_router, palette_router, previews_router, self_draping
from app.modules.ai_analysis.router import router as analysis_router
from app.modules.assessments.router import images as images_router
from app.modules.assessments.router import router as assessments_router
from app.modules.auth.router import router as auth_router
from app.modules.feature_flags.router import router as config_router
from app.modules.users import router as users
from app.modules.commerce import router as commerce
from app.modules.consultations import router as consultations
from app.modules.marketplace import router as marketplace
from app.modules.messaging import router as messaging
from app.modules.promotions import router as promotions
from app.modules.rewards import router as rewards
from app.config.settings import get_settings
from app.core import keep_alive


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    url = keep_alive.resolve(settings.keep_alive_url)
    stop = keep_alive.start(url, settings.keep_alive_minutes) if url else None
    yield
    if stop:
        stop.set()


def create_app() -> FastAPI:
    app = FastAPI(title="Image Consulting API", version="0.1.0", lifespan=lifespan)
    app.add_exception_handler(AppError, app_error_handler)
    origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
    if origins:
        # Bearer tokens, not cookies: no credentials mode needed.
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"],
                           allow_headers=["Authorization", "Content-Type", "Accept-Language"])

    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(auth_router)
    v1.include_router(config_router)
    v1.include_router(assessments_router)
    v1.include_router(images_router)
    v1.include_router(analysis_router)
    v1.include_router(previews_router)
    v1.include_router(tryon_catalogue)
    v1.include_router(colour_types_router)
    v1.include_router(self_draping)
    v1.include_router(palette_router)
    v1.include_router(admin_tryon)
    for r in (
        users.router, users.identity, users.admin,
        commerce.router, commerce.library, commerce.files, commerce.retail, commerce.admin,
        rewards.router, rewards.redeem, rewards.admin,
        marketplace.application, marketplace.practice, marketplace.discovery, marketplace.bookings, marketplace.admin,
        consultations.router, consultations.workspace, consultations.clients, consultations.admin,
        messaging.router, messaging.admin,
        promotions.featured, promotions.ads, promotions.vouchers, promotions.admin,
    ):
        v1.include_router(r)
    if get_settings().env != "production":
        v1.include_router(commerce.sandbox)
    app.include_router(v1)

    vision_paths = ("/api/v1/analysis", "/api/v1/previews", "/api/v1/my-draping", "/api/v1/workspace", "/api/v1/tryon",
                    "/api/v1/admin/tryon-items", "/api/v1/assessment-images")

    @app.middleware("http")
    async def give_back_image_memory(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(vision_paths):
            from app.modules.ai_analysis import engine

            if engine.low_memory():
                engine.trim_memory()
        return response

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
