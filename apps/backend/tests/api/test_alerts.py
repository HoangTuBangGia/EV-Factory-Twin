import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from conftest import make_test_user
from ev_twin_api.api.dependencies import get_current_user
from ev_twin_api.main import app
from ev_twin_api.schemas.alert import AlertCode, AlertSeverity, FactoryAlert
from ev_twin_api.schemas.auth import AppRole
from httpx2 import AsyncClient


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


@pytest.mark.asyncio
async def test_monitor_acknowledges_alert_durably(client: AsyncClient) -> None:
    alert = FactoryAlert(
        id=uuid4(),
        dedupe_key="ROBOT_ERROR:AMR-01",
        severity=AlertSeverity.CRITICAL,
        code=AlertCode.ROBOT_ERROR,
        message="AMR-01 entered ERROR state",
        robot_id="AMR-01",
        timestamp=datetime.now(UTC),
    )
    await app.state.runtime_history_repository.activate_alert(alert)

    response = await client.post(f"/api/v1/alerts/{alert.id}/acknowledge")
    listed = await client.get("/api/v1/alerts")

    assert response.status_code == 200
    assert response.json()["acknowledged_at"] is not None
    assert response.json()["acknowledged_by"] is not None
    persisted = next(item for item in listed.json() if item["id"] == str(alert.id))
    assert persisted["acknowledged_at"] == response.json()["acknowledged_at"]


@pytest.mark.asyncio
async def test_designer_cannot_acknowledge_alert(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: make_test_user(AppRole.DESIGNER)

    response = await client.post(f"/api/v1/alerts/{uuid4()}/acknowledge")

    assert response.status_code == 403
