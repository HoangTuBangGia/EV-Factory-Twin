import asyncio

import pytest
from conftest import make_test_user
from ev_twin_api.api.dependencies import get_current_user
from ev_twin_api.main import app
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.task import Task
from httpx2 import AsyncClient


@pytest.mark.asyncio
async def test_list_tasks_returns_valid_schema(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tasks")

    assert response.status_code == 200
    tasks = [Task.model_validate(item) for item in response.json()]
    assert tasks == []


@pytest.mark.asyncio
async def test_generated_task_appears_in_tasks_endpoint(client: AsyncClient) -> None:
    # speed up generation for this test only; the client fixture builds a fresh
    # FactoryState/MockFactory per test via the lifespan, so this mutation doesn't
    # leak into other tests.
    mock_factory = app.state.mock_factory
    mock_factory.config.task_interval_seconds = 1.0
    mock_factory.config.simulation_speed = 10.0

    await asyncio.sleep(0.35)

    response = await client.get("/api/v1/tasks")

    assert response.status_code == 200
    tasks = [Task.model_validate(item) for item in response.json()]
    assert len(tasks) >= 1
    assert tasks[0].task_id == "TASK-0001"


@pytest.mark.asyncio
async def test_get_unknown_task_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tasks/TASK-9999")

    assert response.status_code == 404
    assert response.json() != {}


@pytest.mark.asyncio
async def test_monitor_queues_transport_task_command(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json={
            "task_id": "TASK-LOCAL-0001",
            "payload_id": "BP-LOCAL-0001",
            "pickup_station_id": "BATTERY_BUFFER",
            "dropoff_station_id": "MARRIAGE_STATION",
            "navigation_timeout_seconds": 30,
            "max_retries": 1,
        },
    )

    assert response.status_code == 202
    assert response.json()["command_type"] == "CREATE_TRANSPORT_TASK"
    assert response.json()["task_id"] == "TASK-LOCAL-0001"
    assert response.json()["scenario_id"] is None
    assert response.json()["status"] == "PENDING"
    assert response.json()["timeout_seconds"] == 30
    assert response.json()["max_retries"] == 1


@pytest.mark.asyncio
async def test_transport_task_must_use_the_active_delivery_route(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json={
            "task_id": "TASK-LOCAL-BAD-ROUTE",
            "payload_id": "BP-LOCAL-BAD-ROUTE",
            "pickup_station_id": "CHARGING_STATION",
            "dropoff_station_id": "MARRIAGE_STATION",
            "navigation_timeout_seconds": 75,
            "max_retries": 2,
        },
    )

    assert response.status_code == 422
    assert "does not serve" in response.json()["detail"]


@pytest.mark.asyncio
async def test_designer_cannot_queue_transport_task(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: make_test_user(AppRole.DESIGNER)
    response = await client.post(
        "/api/v1/tasks",
        json={
            "task_id": "TASK-LOCAL-0002",
            "payload_id": "BP-LOCAL-0002",
            "pickup_station_id": "BATTERY_BUFFER",
            "dropoff_station_id": "MARRIAGE_STATION",
        },
    )
    assert response.status_code == 403
