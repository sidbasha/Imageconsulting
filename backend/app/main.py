from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.errors import AppError, app_error_handler
from app.modules.ai_analysis.router import admin_tryon, catalogue as tryon_catalogue, previews_router
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


def create_app() -> FastAPI:
    app = FastAPI(title="Image Consulting API", version="0.1.0")
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
    v1.include_router(admin_tryon)
    for r in (
        users.router, users.identity, users.admin,
        commerce.router, commerce.library, commerce.files, commerce.retail, commerce.admin,
        rewards.router, rewards.redeem, rewards.admin,
        marketplace.application, marketplace.practice, marketplace.discovery, marketplace.bookings, marketplace.admin,
        consultations.router, consultations.workspace, consultations.admin,
        messaging.router, messaging.admin,
        promotions.featured, promotions.ads, promotions.vouchers, promotions.admin,
    ):
        v1.include_router(r)
    if get_settings().env != "production":
        v1.include_router(commerce.sandbox)
    app.include_router(v1)

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
