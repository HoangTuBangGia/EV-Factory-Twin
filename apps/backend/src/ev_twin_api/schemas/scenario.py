from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ev_twin_api.schemas.base import UtcDatetime


class ScenarioStatus(StrEnum):
    DRAFT = "DRAFT"
    SIMULATED = "SIMULATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


class ScenarioConfig(BaseModel):
    """Inputs shared by the SimPy benchmark and the realtime mock twin.

    Only ``num_robots`` and ``task_arrival_interval`` map to the realtime
    MockFactory. Travel/loading/simulation time and task count are benchmark
    inputs only.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    num_robots: int = Field(ge=1, le=10)
    num_tasks: int = Field(ge=1, le=10_000)
    task_arrival_interval: float = Field(ge=1.0, le=60.0)
    travel_time: float = Field(gt=0.0, le=86_400.0)
    loading_time: float = Field(gt=0.0, le=86_400.0)
    simulation_time: float = Field(gt=0.0, le=86_400.0)
    layout_id: str = Field(default="LAYOUT-DEFAULT", min_length=1, max_length=80)
    layout_version: int = Field(default=1, ge=1)
    route_id: str = Field(default="BATTERY_DELIVERY", min_length=1, max_length=80)
    robot_speed_mps: float = Field(default=1.0, gt=0.0, le=10.0)
    charger_count: int = Field(default=1, ge=1, le=20)
    route_distance_m: float = Field(default=30.0, gt=0.0, le=100_000.0)
    congestion_multiplier: float = Field(default=1.0, ge=1.0, le=10.0)


class ScenarioRunRequest(ScenarioConfig):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value:
            raise ValueError("name must not be blank")
        return value

    def to_config(self) -> ScenarioConfig:
        return ScenarioConfig.model_validate(self.model_dump(exclude={"name"}))


class ScenarioMetrics(BaseModel):
    completed_tasks: int = Field(ge=0)
    unfinished_tasks: int = Field(ge=0)
    completion_rate: float = Field(ge=0.0, le=1.0)
    throughput_per_hour: float = Field(ge=0.0)
    average_cycle_time: float = Field(ge=0.0)
    average_waiting_time: float = Field(ge=0.0)
    fleet_utilization_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    starvation_events: int = Field(default=0, ge=0)
    congestion_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    travel_distance: float = Field(default=0.0, ge=0.0)
    average_delivery_delay: float = Field(default=0.0, ge=0.0)


class Scenario(BaseModel):
    id: str
    name: str
    status: ScenarioStatus
    config: ScenarioConfig
    metrics: ScenarioMetrics
    duration_ms: float = Field(ge=0.0)
    created_at: UtcDatetime
    created_by: UUID | None = None
    reviewed_at: UtcDatetime | None = None
    reviewed_by: UUID | None = None
    applied_at: UtcDatetime | None = None
    applied_by: UUID | None = None
    version: int = Field(default=1, ge=1)

    def with_status(
        self,
        status: ScenarioStatus,
        *,
        reviewed_at: datetime | None = None,
        reviewed_by: UUID | None = None,
        applied_at: datetime | None = None,
        applied_by: UUID | None = None,
    ) -> "Scenario":
        updates: dict[str, object] = {
            "status": status,
            "version": self.version + 1,
        }
        if reviewed_at is not None:
            updates["reviewed_at"] = reviewed_at
        if reviewed_by is not None:
            updates["reviewed_by"] = reviewed_by
        if applied_at is not None:
            updates["applied_at"] = applied_at
        if applied_by is not None:
            updates["applied_by"] = applied_by
        return self.model_copy(update=updates, deep=True)
