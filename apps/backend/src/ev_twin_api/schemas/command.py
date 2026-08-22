from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from ev_twin_api.schemas.base import UtcDatetime
from ev_twin_api.schemas.scenario import ScenarioConfig


class CommandStatus(StrEnum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class CommandAttempt(BaseModel):
    attempt_number: int = Field(ge=1)
    status: CommandStatus
    leased_by: str | None = None
    lease_expires_at: UtcDatetime | None = None
    acknowledged_at: UtcDatetime | None = None
    completed_at: UtcDatetime | None = None
    detail: str = ""


class Command(BaseModel):
    operation_id: UUID
    scenario_id: str
    status: CommandStatus
    payload: ScenarioConfig
    timeout_seconds: float = Field(gt=0.0, le=300.0)
    max_retries: int = Field(ge=0, le=5)
    attempts: list[CommandAttempt]
    requested_by: UUID
    created_at: UtcDatetime
    updated_at: UtcDatetime


class EdgeCommand(BaseModel):
    operation_id: UUID
    attempt_number: int = Field(ge=1)
    scenario_id: str
    payload: ScenarioConfig
    timeout_seconds: float


class CommandAcknowledgementRequest(BaseModel):
    operation_id: UUID
    attempt_number: int = Field(ge=1)
    bridge_id: str = Field(min_length=1, max_length=100)


class CommandResultRequest(CommandAcknowledgementRequest):
    status: CommandStatus
    detail: str = Field(default="", max_length=1000)


class ApplyScenarioRequest(BaseModel):
    timeout_seconds: float = Field(default=30.0, gt=0.0, le=300.0)
    max_retries: int = Field(default=1, ge=0, le=5)
