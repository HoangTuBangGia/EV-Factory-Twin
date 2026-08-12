import asyncio

import pytest
from ev_twin_api.main import app
from ev_twin_api.schemas.alert import FactoryAlert
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_alerts_returns_valid_schema(client: AsyncClient) -> None:
    response = await client.get("/api/v1/alerts")

    assert response.status_code == 200
    alerts = [FactoryAlert.model_validate(item) for item in response.json()]
    assert alerts == []


@pytest.mark.asyncio
async def test_low_battery_alert_appears_in_alerts_endpoint(client: AsyncClient) -> None:
    factory_state = app.state.factory_state
    robot = factory_state.get_robot("AMR-01")
    robot.battery = 10.0
    factory_state.update_robot(robot)

    await asyncio.sleep(0.3)

    response = await client.get("/api/v1/alerts")

    assert response.status_code == 200
    alerts = [FactoryAlert.model_validate(item) for item in response.json()]
    low_battery_alerts = [alert for alert in alerts if alert.code == "LOW_BATTERY"]
    assert len(low_battery_alerts) == 1
    assert low_battery_alerts[0].robot_id == "AMR-01"
