import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, cast
from uuid import uuid4

from ev_sim.layout import route_profile
from ev_sim.logistics import LogisticsConfig, run_logistics_simulation
from ev_sim.scenario import load_scenario
from fastapi import Depends, Request

from ev_twin_api.schemas.auth import CurrentUser
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.scenario import (
    Scenario,
    ScenarioConfig,
    ScenarioMetrics,
    ScenarioRunRequest,
    ScenarioStatus,
)
from ev_twin_api.services.layout_service import LayoutNotFoundError, LayoutService
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.scenario_repository import (
    InMemoryScenarioRepository,
    ScenarioRepository,
    ScenarioRepositoryConflictError,
    ScenarioRepositoryNotFoundError,
)

logger = logging.getLogger("ev_twin_api")

BASELINE_PATH = (
    Path(__file__).resolve().parents[5] / "services" / "simulation" / "scenarios" / "baseline.json"
)


class ScenarioNotFoundError(LookupError):
    pass


class InvalidScenarioTransitionError(RuntimeError):
    pass


class InvalidScenarioConfigurationError(ValueError):
    pass


def _run_logistics(config: ScenarioConfig) -> tuple[ScenarioMetrics, float]:
    started_at = time.perf_counter()
    result = run_logistics_simulation(
        LogisticsConfig(
            robot_count=config.num_robots,
            task_count=config.num_tasks,
            demand_interval_seconds=config.task_arrival_interval,
            route_distance_m=config.route_distance_m,
            robot_speed_mps=config.robot_speed_mps,
            loading_time_seconds=config.loading_time,
            simulation_time_seconds=config.simulation_time,
            charger_count=config.charger_count,
            congestion_multiplier=config.congestion_multiplier,
        )
    )
    duration_ms = (time.perf_counter() - started_at) * 1000.0
    kpi = result.metrics
    return (
        ScenarioMetrics(
            completed_tasks=kpi.completed_tasks,
            unfinished_tasks=kpi.unfinished_tasks,
            completion_rate=kpi.completion_rate,
            throughput_per_hour=kpi.throughput_per_hour,
            average_cycle_time=kpi.average_cycle_time,
            average_waiting_time=kpi.average_waiting_time,
            fleet_utilization_percent=kpi.fleet_utilization_percent,
            starvation_events=kpi.starvation_events,
            congestion_percent=kpi.congestion_percent,
            travel_distance=kpi.travel_distance,
            average_delivery_delay=kpi.average_delivery_delay,
        ),
        duration_ms,
    )


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
    """Runs benchmarks and owns workflow rules independently of persistence."""

    def __init__(
        self,
        mock_factory: MockFactory,
        *,
        layout_service: LayoutService,
        repository: ScenarioRepository | None = None,
    ) -> None:
        self._mock_factory = mock_factory
        self._repository = repository or InMemoryScenarioRepository()
        self._layout_service = layout_service
        self._baseline: Scenario | None = None

    async def run(self, request: ScenarioRunRequest, actor: CurrentUser) -> Scenario:
        config = request.to_config()
        # The bounded MVP workload (at most 10,000 tasks) completes quickly
        # enough to run inline. Keeping it local also makes sequential runs
        # deterministic without coordinating a process-wide executor.
        config = await self._resolve_layout(config)
        metrics, duration_ms = _run_logistics(config)

        return await self._repository.create(
            name=request.name,
            config=config,
            metrics=metrics,
            duration_ms=duration_ms,
            actor=actor,
            request_id=uuid4(),
            created_at=datetime.now(UTC),
        )

    async def validate_request(self, request: ScenarioRunRequest) -> None:
        config = request.to_config()
        await self._resolve_layout(config)

    async def _resolve_layout(self, config: ScenarioConfig) -> ScenarioConfig:
        try:
            layout = await self._layout_service.get(config.layout_id, config.layout_version)
            profile = route_profile(layout, config.route_id)
        except (LayoutNotFoundError, ValueError) as error:
            raise InvalidScenarioConfigurationError(str(error)) from error
        return config.model_copy(
            update={
                "route_distance_m": profile.distance_m,
                "congestion_multiplier": profile.congestion_multiplier,
                "travel_time": (
                    profile.distance_m / config.robot_speed_mps * profile.congestion_multiplier
                ),
            }
        )

    async def get_baseline(self) -> Scenario:
        cached = self._baseline
        if cached is not None:
            return cached.model_copy(deep=True)

        request = _load_baseline_request()
        config = await self._resolve_layout(request.to_config())
        metrics, duration_ms = _run_logistics(config)
        baseline = Scenario(
            id="baseline",
            name=request.name,
            status=ScenarioStatus.SIMULATED,
            config=config,
            metrics=metrics,
            duration_ms=duration_ms,
            created_at=datetime.now(UTC),
            created_by=None,
            version=1,
        )
        if self._baseline is None:
            self._baseline = baseline
        return self._baseline.model_copy(deep=True)

    async def list(self) -> list[Scenario]:
        return await self._repository.list()

    async def get(self, scenario_id: str) -> Scenario:
        scenario = await self._repository.get(scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(f"Scenario '{scenario_id}' not found")
        return scenario

    async def approve(self, scenario_id: str, actor: CurrentUser) -> Scenario:
        return await self._review(scenario_id, ScenarioStatus.APPROVED, actor)

    async def reject(self, scenario_id: str, actor: CurrentUser) -> Scenario:
        return await self._review(scenario_id, ScenarioStatus.REJECTED, actor)

    async def apply(self, scenario_id: str, actor: CurrentUser) -> Scenario:
        scenario = await self.get(scenario_id)
        if scenario.status != ScenarioStatus.APPROVED:
            raise InvalidScenarioTransitionError(
                f"Scenario '{scenario_id}' must be APPROVED before apply; "
                f"current status is {scenario.status}"
            )
        self._ensure_independent_actor(scenario, actor)

        async with self._mock_factory.exclusive_control():
            return await self._apply_exclusively(scenario, actor)

    async def _apply_exclusively(self, scenario: Scenario, actor: CurrentUser) -> Scenario:
        """Apply one approved scenario while all factory controls are serialized."""

        previous_config = self._mock_factory.config.model_copy(deep=True)
        realtime_config = MockFactoryConfig(
            robot_count=scenario.config.num_robots,
            task_interval_seconds=scenario.config.task_arrival_interval,
            robot_speed_mps=scenario.config.robot_speed_mps,
            simulation_speed=previous_config.simulation_speed,
            low_battery_threshold=previous_config.low_battery_threshold,
        )
        factory_mutation_started = False

        async def apply_before_database_commit(_: Scenario) -> None:
            nonlocal factory_mutation_started
            factory_mutation_started = True
            self._mock_factory.apply_config(realtime_config)
            await self._mock_factory.reset()

        try:
            return await self._repository.transition(
                before=scenario,
                expected_status=ScenarioStatus.APPROVED,
                new_status=ScenarioStatus.APPLIED,
                actor=actor,
                request_id=uuid4(),
                occurred_at=datetime.now(UTC),
                before_commit=apply_before_database_commit,
            )
        except Exception as error:
            # PostgreSQL and the realtime in-memory factory cannot share a true
            # distributed transaction. The row is conditionally updated first
            # while locked; if reset/audit/commit fails, restore the old factory
            # config and reset once more. A failed compensation is logged loudly.
            if factory_mutation_started:
                try:
                    self._mock_factory.apply_config(previous_config)
                    await self._mock_factory.reset()
                except Exception:
                    logger.exception(
                        "failed to compensate mock factory after scenario apply error",
                        extra={"scenario_id": scenario.id},
                    )
            self._raise_domain_repository_error(error)
            raise

    async def _review(
        self,
        scenario_id: str,
        status: ScenarioStatus,
        actor: CurrentUser,
    ) -> Scenario:
        scenario = await self.get(scenario_id)
        if scenario.status != ScenarioStatus.SIMULATED:
            raise InvalidScenarioTransitionError(
                f"Scenario '{scenario_id}' cannot transition from {scenario.status} to {status}"
            )
        self._ensure_independent_actor(scenario, actor)
        try:
            return await self._repository.transition(
                before=scenario,
                expected_status=ScenarioStatus.SIMULATED,
                new_status=status,
                actor=actor,
                request_id=uuid4(),
                occurred_at=datetime.now(UTC),
            )
        except Exception as error:
            self._raise_domain_repository_error(error)
            raise

    @staticmethod
    def _ensure_independent_actor(scenario: Scenario, actor: CurrentUser) -> None:
        if scenario.created_by == actor.id:
            raise InvalidScenarioTransitionError(
                f"Scenario '{scenario.id}' creator cannot review or apply their own scenario"
            )

    @staticmethod
    def _raise_domain_repository_error(error: Exception) -> None:
        if isinstance(error, ScenarioRepositoryNotFoundError):
            raise ScenarioNotFoundError(str(error)) from error
        if isinstance(error, ScenarioRepositoryConflictError):
            raise InvalidScenarioTransitionError(str(error)) from error


def get_scenario_service(request: Request) -> ScenarioService:
    return cast(ScenarioService, request.app.state.scenario_service)


ScenarioServiceDep = Annotated[ScenarioService, Depends(get_scenario_service)]
