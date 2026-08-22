from itertools import product

from ev_twin_api.schemas.auth import CurrentUser
from ev_twin_api.schemas.optimization import (
    OptimizationRequest,
    OptimizationResult,
    RankedScenario,
)
from ev_twin_api.schemas.scenario import Scenario, ScenarioRunRequest
from ev_twin_api.services.scenario_service import ScenarioService


class OptimizationService:
    def __init__(self, scenarios: ScenarioService) -> None:
        self._scenarios = scenarios

    async def run(self, request: OptimizationRequest, actor: CurrentUser) -> OptimizationResult:
        scenarios: list[Scenario] = []
        candidate_requests: list[ScenarioRunRequest] = []
        combinations = product(
            request.layouts,
            request.route_ids,
            request.robot_counts,
            request.robot_speeds_mps,
            request.charger_counts,
            request.demand_intervals,
        )
        for index, (layout, route, robots, speed, chargers, demand) in enumerate(
            combinations, start=1
        ):
            candidate_requests.append(
                ScenarioRunRequest(
                    name=f"{request.name_prefix}-{index:02d}",
                    layout_id=layout.layout_id,
                    layout_version=layout.layout_version,
                    route_id=route,
                    num_robots=robots,
                    robot_speed_mps=speed,
                    charger_count=chargers,
                    task_arrival_interval=demand,
                    num_tasks=request.num_tasks,
                    loading_time=request.loading_time,
                    simulation_time=request.simulation_time,
                    travel_time=1.0,
                )
            )

        for candidate in candidate_requests:
            await self._scenarios.validate_request(candidate)
        for candidate in candidate_requests:
            scenarios.append(await self._scenarios.run(candidate, actor))

        ranked = sorted(scenarios, key=self._rank_key)
        return OptimizationResult(
            evaluated_candidates=len(ranked),
            recommendation=ranked[0],
            ranking=[
                RankedScenario(rank=index, scenario=scenario)
                for index, scenario in enumerate(ranked, start=1)
            ],
        )

    @staticmethod
    def _rank_key(scenario: Scenario) -> tuple[float, ...]:
        metrics = scenario.metrics
        return (
            -metrics.completion_rate,
            -metrics.throughput_per_hour,
            metrics.average_delivery_delay,
            float(metrics.starvation_events),
            metrics.congestion_percent,
            metrics.average_cycle_time,
            -metrics.fleet_utilization_percent,
            metrics.travel_distance,
            float(scenario.config.num_robots),
            float(scenario.config.charger_count),
            scenario.config.robot_speed_mps,
        )
