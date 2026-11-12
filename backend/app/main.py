from fastapi import APIRouter, FastAPI

from app.core.errors import AppError, app_error_handler
from app.modules.ai_analysis.router import previews_router
from app.modules.ai_analysis.router import router as analysis_router
from app.modules.assessments.router import images as images_router
from app.modules.assessments.router import router as assessments_router
from app.modules.auth.router import router as auth_router
from app.modules.feature_flags.router import router as config_router
from app.modules.phase_management.router import router as phase_router


def create_app() -> FastAPI:
    app = FastAPI(title="Image Consulting API", version="0.1.0")
    app.add_exception_handler(AppError, app_error_handler)

    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(auth_router)
    v1.include_router(config_router)
    v1.include_router(phase_router)
    v1.include_router(assessments_router)
    v1.include_router(images_router)
    v1.include_router(analysis_router)
    v1.include_router(previews_router)
    app.include_router(v1)

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
