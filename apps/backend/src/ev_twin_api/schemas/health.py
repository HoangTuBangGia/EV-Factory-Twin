from typing import Literal

from pydantic import BaseModel

from ev_twin_api.schemas.base import UtcDatetime


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app_env: str
    version: str
    uptime_seconds: float
    timestamp: UtcDatetime
