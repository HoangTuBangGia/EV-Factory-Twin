import asyncio
import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, cast
from uuid import uuid4

from ev_sim.layout import route_profile
from ev_sim.logistics import LogisticsConfig, run_logistics_simulation
from ev_sim.scenario import load_scenario
from fastapi import Depends, Request
from twin_core.models.layout import LayoutVersion

from ev_twin_api.schemas.auth import CurrentUser
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.scenario import (
    Scenario,
    ScenarioConfig,
    ScenarioMetrics,
    ScenarioRevisionRequest,
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


async def _run_logistics_off_loop(config: ScenarioConfig) -> tuple[ScenarioMetrics, float]:
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="scenario-sim") as executor:
        return await loop.run_in_executor(executor, _run_logistics, config)


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
        applied_layout_sink: Callable[[LayoutVersion], None] | None = None,
        apply_to_mock_runtime: bool = True,
    ) -> None:
        self._mock_factory = mock_factory
        self._repository = repository or InMemoryScenarioRepository()
        self._layout_service = layout_service
        self._applied_layout_sink = applied_layout_sink
        self._apply_to_mock_runtime = apply_to_mock_runtime
        self._baseline: Scenario | None = None

    async def run(self, request: ScenarioRunRequest, actor: CurrentUser) -> Scenario:
        if request.revision_of is not None:
            source = await self.get(request.revision_of)
            if source.status != ScenarioStatus.REVISION_REQUESTED or source.created_by != actor.id:
                raise InvalidScenarioTransitionError(
                    f"Scenario '{request.revision_of}' cannot be revised by this actor"
                )
        config = request.to_config()
        config = await self._resolve_layout(config)
        metrics, duration_ms = await _run_logistics_off_loop(config)

        return await self._repository.create(
            name=request.name,
            config=config,
            metrics=metrics,
            duration_ms=duration_ms,
            actor=actor,
            revision_of=request.revision_of,
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
        metrics, duration_ms = await _run_logistics_off_loop(config)
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

    async def get_applied_layout(self) -> LayoutVersion | None:
        applied = await self.get_applied_scenario()
        if applied is None:
            return None
        return await self._layout_service.get(
            applied.config.layout_id, applied.config.layout_version
        )

    async def get_applied_scenario(self) -> Scenario | None:
        applied = [
            scenario
            for scenario in await self._repository.list()
            if scenario.status == ScenarioStatus.APPLIED
        ]
        if not applied:
            return None
        return max(applied, key=lambda scenario: scenario.applied_at or scenario.created_at)

    async def approve(self, scenario_id: str, actor: CurrentUser) -> Scenario:
        return await self._review(scenario_id, ScenarioStatus.APPROVED, actor)

    async def submit(self, scenario_id: str, actor: CurrentUser) -> Scenario:
        scenario = await self.get(scenario_id)
        if scenario.status != ScenarioStatus.SIMULATED:
            raise InvalidScenarioTransitionError(
                f"Scenario '{scenario_id}' cannot transition from {scenario.status} to SUBMITTED"
            )
        try:
            return await self._repository.transition(
                before=scenario,
                expected_status=ScenarioStatus.SIMULATED,
                new_status=ScenarioStatus.SUBMITTED,
                actor=actor,
                request_id=uuid4(),
                occurred_at=datetime.now(UTC),
            )
        except Exception as error:
            self._raise_domain_repository_error(error)
            raise

    async def reject(self, scenario_id: str, actor: CurrentUser) -> Scenario:
        return await self._review(scenario_id, ScenarioStatus.REJECTED, actor)

    async def request_revision(
        self,
        scenario_id: str,
        request: ScenarioRevisionRequest,
        actor: CurrentUser,
    ) -> Scenario:
        return await self._review(
            scenario_id,
            ScenarioStatus.REVISION_REQUESTED,
            actor,
            review_note=request.note,
        )

    async def complete_apply(self, scenario_id: str, actor: CurrentUser) -> Scenario:
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
        previous_layout = self._mock_factory.layout
        previous_route_id = self._mock_factory.route_id
        layout = await self._layout_service.get(
            scenario.config.layout_id, scenario.config.layout_version
        )
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
            if not self._apply_to_mock_runtime:
                return
            factory_mutation_started = True
            self._mock_factory.apply_layout(layout, scenario.config.route_id)
            self._mock_factory.apply_config(realtime_config)
            await self._mock_factory.reset()

        try:
            applied = await self._repository.transition(
                before=scenario,
                expected_status=ScenarioStatus.APPROVED,
                new_status=ScenarioStatus.APPLIED,
                actor=actor,
                request_id=uuid4(),
                occurred_at=datetime.now(UTC),
                before_commit=apply_before_database_commit,
            )
            if self._applied_layout_sink is not None:
                self._applied_layout_sink(layout)
            return applied
        except Exception as error:
            # PostgreSQL and the realtime in-memory factory cannot share a true
            # distributed transaction. The row is conditionally updated first
            # while locked; if reset/audit/commit fails, restore the old factory
            # config and reset once more. A failed compensation is logged loudly.
            if factory_mutation_started:
                try:
                    self._mock_factory.apply_layout(previous_layout, previous_route_id)
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
        review_note: str | None = None,
    ) -> Scenario:
        scenario = await self.get(scenario_id)
        if scenario.status != ScenarioStatus.SUBMITTED:
            raise InvalidScenarioTransitionError(
                f"Scenario '{scenario_id}' cannot transition from {scenario.status} to {status}"
            )
        self._ensure_independent_actor(scenario, actor)
        try:
            return await self._repository.transition(
                before=scenario,
                expected_status=ScenarioStatus.SUBMITTED,
                new_status=status,
                actor=actor,
                request_id=uuid4(),
                occurred_at=datetime.now(UTC),
                review_note=review_note,
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
