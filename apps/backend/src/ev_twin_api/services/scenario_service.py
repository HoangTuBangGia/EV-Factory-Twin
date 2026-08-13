import asyncio
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, cast

from ev_sim.config import SimulationConfig as SimPyConfig
from ev_sim.metrics import calculate_metrics
from ev_sim.runner import run_simulation
from ev_sim.scenario import load_scenario
from fastapi import Depends, Request

from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.scenario import (
    Scenario,
    ScenarioConfig,
    ScenarioMetrics,
    ScenarioRunRequest,
    ScenarioStatus,
)
from ev_twin_api.services.mock_factory import MockFactory

logger = logging.getLogger("ev_twin_api")

BASELINE_PATH = (
    Path(__file__).resolve().parents[5] / "services" / "simulation" / "scenarios" / "baseline.json"
)


class ScenarioNotFoundError(LookupError):
    pass


class InvalidScenarioTransitionError(RuntimeError):
    pass


def _run_benchmark(name: str, config: ScenarioConfig) -> tuple[ScenarioMetrics, float]:
    sim_config = SimPyConfig(name=name, **config.model_dump())
    started_at = time.perf_counter()
    records = run_simulation(sim_config)
    result = calculate_metrics(
        records,
        simulation_time=sim_config.simulation_time,
        total_tasks=sim_config.num_tasks,
    )
    duration_ms = (time.perf_counter() - started_at) * 1000.0
    metrics = ScenarioMetrics(
        completed_tasks=result.completed_tasks,
        unfinished_tasks=result.unfinished_tasks,
        completion_rate=result.completion_rate,
        throughput_per_hour=result.throughput_per_hour,
        average_cycle_time=result.average_cycle_time,
        average_waiting_time=result.average_waiting_time,
    )
    return metrics, duration_ms


def _load_baseline_request() -> ScenarioRunRequest:
    config = load_scenario(BASELINE_PATH)
    return ScenarioRunRequest(
        name=config.name,
        num_robots=config.num_robots,
        num_tasks=config.num_tasks,
        task_arrival_interval=config.task_arrival_interval,
        travel_time=config.travel_time,
        loading_time=config.loading_time,
        simulation_time=config.simulation_time,
    )


class ScenarioService:
    """Runs benchmark scenarios and owns their MVP in-memory workflow state."""

    def __init__(self, mock_factory: MockFactory) -> None:
        self._mock_factory = mock_factory
        self._scenarios: dict[str, Scenario] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()
        self._baseline: Scenario | None = None

    async def run(self, request: ScenarioRunRequest) -> Scenario:
        config = request.to_config()
        # The bounded MVP workload (at most 10,000 tasks) completes quickly
        # enough to run inline. Keeping it local also makes sequential runs
        # deterministic without coordinating a process-wide executor.
        metrics, duration_ms = _run_benchmark(request.name, config)

        async with self._lock:
            scenario_id = f"SCN-{self._next_id:04d}"
            self._next_id += 1
            scenario = Scenario(
                id=scenario_id,
                name=request.name,
                status=ScenarioStatus.SIMULATED,
                config=config,
                metrics=metrics,
                duration_ms=duration_ms,
            )
            self._scenarios[scenario_id] = scenario
            return scenario.model_copy(deep=True)

    async def get_baseline(self) -> Scenario:
        async with self._lock:
            cached = self._baseline
        if cached is not None:
            return cached.model_copy(deep=True)

        request = _load_baseline_request()
        config = request.to_config()
        metrics, duration_ms = _run_benchmark(request.name, config)
        baseline = Scenario(
            id="baseline",
            name=request.name,
            status=ScenarioStatus.SIMULATED,
            config=config,
            metrics=metrics,
            duration_ms=duration_ms,
        )
        async with self._lock:
            if self._baseline is None:
                self._baseline = baseline
            return self._baseline.model_copy(deep=True)

    async def list(self) -> list[Scenario]:
        async with self._lock:
            return [scenario.model_copy(deep=True) for scenario in self._scenarios.values()]

    async def get(self, scenario_id: str) -> Scenario:
        async with self._lock:
            return self._get_stored(scenario_id).model_copy(deep=True)

    async def approve(self, scenario_id: str) -> Scenario:
        return await self._review(scenario_id, ScenarioStatus.APPROVED)

    async def reject(self, scenario_id: str) -> Scenario:
        return await self._review(scenario_id, ScenarioStatus.REJECTED)

    async def apply(self, scenario_id: str) -> Scenario:
        async with self._lock:
            scenario = self._get_stored(scenario_id)
            if scenario.status != ScenarioStatus.APPROVED:
                raise InvalidScenarioTransitionError(
                    f"Scenario '{scenario_id}' must be APPROVED before apply; "
                    f"current status is {scenario.status}"
                )

            current = self._mock_factory.config
            realtime_config = MockFactoryConfig(
                robot_count=scenario.config.num_robots,
                task_interval_seconds=scenario.config.task_arrival_interval,
                robot_speed_mps=current.robot_speed_mps,
                simulation_speed=current.simulation_speed,
                low_battery_threshold=current.low_battery_threshold,
            )
            self._mock_factory.apply_config(realtime_config)
            await self._mock_factory.reset()

            applied = scenario.with_status(ScenarioStatus.APPLIED, applied_at=datetime.now(UTC))
            self._scenarios[scenario_id] = applied
            return applied.model_copy(deep=True)

    async def _review(self, scenario_id: str, status: ScenarioStatus) -> Scenario:
        async with self._lock:
            scenario = self._get_stored(scenario_id)
            if scenario.status != ScenarioStatus.SIMULATED:
                raise InvalidScenarioTransitionError(
                    f"Scenario '{scenario_id}' cannot transition from {scenario.status} to {status}"
                )
            reviewed = scenario.with_status(status, reviewed_at=datetime.now(UTC))
            self._scenarios[scenario_id] = reviewed
            return reviewed.model_copy(deep=True)

    def _get_stored(self, scenario_id: str) -> Scenario:
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(f"Scenario '{scenario_id}' not found")
        return scenario


def get_scenario_service(request: Request) -> ScenarioService:
    return cast(ScenarioService, request.app.state.scenario_service)


ScenarioServiceDep = Annotated[ScenarioService, Depends(get_scenario_service)]
