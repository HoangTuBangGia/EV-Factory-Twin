from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, field_serializer


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app_env: str
    version: str
    uptime_seconds: float
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
