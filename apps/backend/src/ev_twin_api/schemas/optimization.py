from pydantic import BaseModel, ConfigDict, Field, model_validator

from ev_twin_api.schemas.scenario import Scenario


class LayoutCandidate(BaseModel):
    layout_id: str = Field(min_length=1, max_length=80)
    layout_version: int = Field(ge=1)


class OptimizationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name_prefix: str = Field(min_length=1, max_length=50)
    layouts: list[LayoutCandidate] = Field(min_length=1, max_length=8)
    route_ids: list[str] = Field(min_length=1, max_length=8)
    robot_counts: list[int] = Field(min_length=1, max_length=8)
    robot_speeds_mps: list[float] = Field(min_length=1, max_length=8)
    charger_counts: list[int] = Field(min_length=1, max_length=8)
    demand_intervals: list[float] = Field(min_length=1, max_length=8)
    num_tasks: int = Field(default=100, ge=1, le=10_000)
    loading_time: float = Field(default=5.0, gt=0.0, le=86_400.0)
    simulation_time: float = Field(default=3_600.0, gt=0.0, le=86_400.0)

    @model_validator(mode="after")
    def bounded_search(self) -> "OptimizationRequest":
        dimensions = (
            self.layouts,
            self.route_ids,
            self.robot_counts,
            self.robot_speeds_mps,
            self.charger_counts,
            self.demand_intervals,
        )
        candidate_count = 1
        for dimension in dimensions:
            candidate_count *= len(dimension)
        if candidate_count > 64:
            raise ValueError("optimization search is limited to 64 candidates")
        if any(not 1 <= value <= 10 for value in self.robot_counts):
            raise ValueError("robot_counts values must be in [1, 10]")
        if any(not 0.0 < value <= 10.0 for value in self.robot_speeds_mps):
            raise ValueError("robot_speeds_mps values must be in (0, 10]")
        if any(not 1 <= value <= 20 for value in self.charger_counts):
            raise ValueError("charger_counts values must be in [1, 20]")
        if any(not 1.0 <= value <= 60.0 for value in self.demand_intervals):
            raise ValueError("demand_intervals values must be in [1, 60]")
        return self


class RankedScenario(BaseModel):
    rank: int = Field(ge=1)
    scenario: Scenario


class OptimizationResult(BaseModel):
    evaluated_candidates: int = Field(ge=1, le=64)
    recommendation: Scenario
    ranking: list[RankedScenario]
