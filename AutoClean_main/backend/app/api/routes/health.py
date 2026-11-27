from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.models.interfaces import model_registry
from backend.app.schemas.responses import HealthResponse, ModelAvailability

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health():
    settings = get_settings()
    model_registry.load_once(settings)
    return HealthResponse(
        status="ok",
        models={
            "tabular": ModelAvailability(**model_registry.models["tabular"].health_payload()),
            "image": ModelAvailability(**model_registry.models["image"].health_payload()),
        },
        upload_limit_bytes=settings.max_upload_bytes,
    )
