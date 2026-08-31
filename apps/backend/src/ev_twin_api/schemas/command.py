from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ev_twin_api.schemas.base import UtcDatetime
from ev_twin_api.schemas.scenario import ScenarioConfig
from ev_twin_api.schemas.task import CreateTransportTaskRequest


class CommandType(StrEnum):
    APPLY_SCENARIO = "APPLY_SCENARIO"
    CREATE_TRANSPORT_TASK = "CREATE_TRANSPORT_TASK"


class CommandStatus(StrEnum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    COMPLETED = "COMPLETED"
    REQUIRES_RELAUNCH = "REQUIRES_RELAUNCH"
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
    command_type: CommandType = CommandType.APPLY_SCENARIO
    scenario_id: str | None = None
    task_id: str | None = None
    status: CommandStatus
    payload: ScenarioConfig | CreateTransportTaskRequest
    timeout_seconds: float = Field(gt=0.0, le=300.0)
    max_retries: int = Field(ge=0, le=5)
    attempts: list[CommandAttempt]
    requested_by: UUID
    created_at: UtcDatetime
    updated_at: UtcDatetime

    @model_validator(mode="after")
    def validate_target_and_payload(self) -> "Command":
        if self.command_type == CommandType.APPLY_SCENARIO:
            if self.scenario_id is None or self.task_id is not None:
                raise ValueError("apply command requires only scenario_id")
            if not isinstance(self.payload, ScenarioConfig):
                raise ValueError("apply command requires scenario payload")
        else:
            if self.task_id is None or self.scenario_id is not None:
                raise ValueError("task command requires only task_id")
            if not isinstance(self.payload, CreateTransportTaskRequest):
                raise ValueError("task command requires transport-task payload")
        return self


class EdgeCommand(BaseModel):
    operation_id: UUID
    attempt_number: int = Field(ge=1)
    command_type: CommandType
    scenario_id: str | None = None
    task_id: str | None = None
    payload: ScenarioConfig | CreateTransportTaskRequest
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


class ScenarioCompatibilityStatus(StrEnum):
    LIVE_APPLY = "LIVE_APPLY"
    REQUIRES_RELAUNCH = "REQUIRES_RELAUNCH"
    RUNTIME_UNAVAILABLE = "RUNTIME_UNAVAILABLE"


class ScenarioCompatibility(BaseModel):
    status: ScenarioCompatibilityStatus
    details: list[str]
    dynamic_updates: list[str] = Field(default_factory=list)
