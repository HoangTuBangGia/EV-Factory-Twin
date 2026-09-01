from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from conftest import make_test_user
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.scenario import ScenarioRunRequest
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.layout_service import LayoutService
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.scenario_service import ScenarioService
from ev_twin_api.services.websocket_manager import WebSocketManager
from twin_core.models.layout import LayoutVersion


@pytest.mark.asyncio
async def test_scenario_derives_route_profile_and_authoritative_kpis() -> None:
    layout = LayoutVersion.model_validate(
        {
            "layout_id": "LAYOUT-TEST",
            "name": "Test",
            "version": 2,
            "created_by": make_test_user(AppRole.DESIGNER).id,
            "created_at": datetime.now(UTC),
            "width": 20,
            "height": 20,
            "stations": [
                {"id": "BUFFER", "type": "BATTERY_BUFFER", "x": 0, "y": 0},
                {"id": "MARRIAGE", "type": "MARRIAGE_STATION", "x": 10, "y": 0},
                {"id": "CHARGER", "type": "CHARGING_STATION", "x": 0, "y": 10},
            ],
            "routes": [
                {
                    "id": "DELIVERY",
                    "start_station_id": "BUFFER",
                    "end_station_id": "MARRIAGE",
                    "waypoints": [{"x": 0, "y": 0}, {"x": 10, "y": 0}],
                }
            ],
            "no_go_zones": [],
            "congestion_zones": [],
            "config": {},
        }
    )
    layouts = AsyncMock(spec=LayoutService)
    layouts.get.return_value = layout
    factory_config = MockFactoryConfig()
    factory = MockFactory(
        FactoryState(factory_config), factory_config, WebSocketManager(), enabled=False
    )
    service = ScenarioService(factory, layout_service=layouts)

    scenario = await service.run(
        ScenarioRunRequest(
            name="layout-bound",
            layout_id="LAYOUT-TEST",
            layout_version=2,
            route_id="DELIVERY",
            num_robots=2,
            num_tasks=2,
            task_arrival_interval=2.0,
            travel_time=1.0,
            loading_time=1.0,
            simulation_time=100.0,
        ),
        make_test_user(AppRole.DESIGNER),
    )

    assert scenario.config.route_distance_m == 10.0
    assert scenario.config.travel_time == pytest.approx(10.0 / 1.2)
    assert scenario.metrics.completed_tasks == 2
    assert scenario.metrics.travel_distance == 20.0
    assert scenario.metrics.fleet_utilization_percent > 0.0
