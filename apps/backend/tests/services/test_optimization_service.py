from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from conftest import make_test_user
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.optimization import LayoutCandidate, OptimizationRequest
from ev_twin_api.schemas.scenario import Scenario, ScenarioConfig, ScenarioMetrics, ScenarioStatus
from ev_twin_api.services.optimization_service import OptimizationService
from pydantic import ValidationError


def request(**updates: object) -> OptimizationRequest:
    values: dict[str, object] = {
        "name_prefix": "flow",
        "layouts": [LayoutCandidate(layout_id="LAYOUT-DEFAULT", layout_version=1)],
        "route_ids": ["BATTERY_DELIVERY"],
        "robot_counts": [2, 3],
        "robot_speeds_mps": [1.0],
        "charger_counts": [1],
        "demand_intervals": [8.0],
    }
    values.update(updates)
    return OptimizationRequest.model_validate(values)


def scenario(identifier: str, completion: float, robots: int) -> Scenario:
    return Scenario(
        id=identifier,
        name=identifier,
        status=ScenarioStatus.SIMULATED,
        config=ScenarioConfig(
            num_robots=robots,
            num_tasks=10,
            task_arrival_interval=8.0,
            travel_time=10.0,
            loading_time=2.0,
            simulation_time=100.0,
        ),
        metrics=ScenarioMetrics(
            completed_tasks=int(completion * 10),
            unfinished_tasks=10 - int(completion * 10),
            completion_rate=completion,
            throughput_per_hour=completion * 360.0,
            average_cycle_time=20.0,
            average_waiting_time=1.0,
        ),
        duration_ms=1.0,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_optimizer_persists_and_ranks_deterministic_candidates() -> None:
    scenarios = AsyncMock()
    scenarios.run.side_effect = [scenario("SCN-1", 0.8, 2), scenario("SCN-2", 1.0, 3)]
    service = OptimizationService(scenarios)

    result = await service.run(request(), make_test_user(AppRole.DESIGNER))

    assert result.evaluated_candidates == 2
    assert result.recommendation.id == "SCN-2"
    assert [item.scenario.id for item in result.ranking] == ["SCN-2", "SCN-1"]
    assert scenarios.run.await_count == 2


def test_optimizer_rejects_more_than_64_candidates() -> None:
    with pytest.raises(ValidationError, match="64 candidates"):
        request(
            robot_counts=list(range(1, 9)),
            robot_speeds_mps=[0.5, 1.0, 1.5],
            charger_counts=[1, 2, 3],
        )
