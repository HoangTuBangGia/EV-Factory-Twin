import time
from datetime import UTC, datetime

from fastapi import APIRouter, Request

from ev_twin_api import __version__
from ev_twin_api.core.config import get_settings
from ev_twin_api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = get_settings()
    started_at = request.app.state.started_at_monotonic
    return HealthResponse(
        status="ok",
        app_env=settings.app_env,
        version=__version__,
        uptime_seconds=time.monotonic() - started_at,
        timestamp=datetime.now(UTC),
    )
