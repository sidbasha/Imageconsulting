from fastapi import APIRouter, Depends

from app.modules.feature_flags.guard import request_release
from app.modules.phase_management import service

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/features")
def enabled_features(current: dict = Depends(request_release)) -> dict:
    """What the mobile app and admin panel build their navigation from.
    Lists enabled items only; disabled phases and features are not named."""
    snapshot = current["snapshot"]
    features = sorted(service.effective_keys(snapshot))
    return {
        "release_version": current["release"].version,
        "preview": current["preview"],
        "phases": sorted({snapshot["features"][key]["phase"] for key in features}),
        "features": features,
    }
