from collections.abc import AsyncIterator
from functools import partial

import pytest
import pytest_asyncio
from conftest import make_test_user
from ev_twin_api.api.dependencies import get_current_user
from ev_twin_api.core.config import Settings, get_settings
from ev_twin_api.main import app
from ev_twin_api.schemas.auth import AppRole
from httpx2 import AsyncClient

EDGE_SECRET = "0123456789abcdef0123456789abcdef"
SCENARIO = {
    "name": "command-flow",
    "num_robots": 3,
    "num_tasks": 10,
    "task_arrival_interval": 8.0,
    "travel_time": 1.0,
    "loading_time": 2.0,
    "simulation_time": 100.0,
}


@pytest_asyncio.fixture
async def edge_client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, edge_telemetry_shared_secret=EDGE_SECRET
    )
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_apply_command_edge_ack_and_completion(edge_client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = partial(make_test_user, AppRole.DESIGNER)
    scenario_id = (await edge_client.post("/api/v1/scenarios/run", json=SCENARIO)).json()["id"]
    submitted = await edge_client.post(f"/api/v1/scenarios/{scenario_id}/submit")
    assert submitted.json()["status"] == "SUBMITTED"

    app.dependency_overrides[get_current_user] = partial(make_test_user, AppRole.MONITOR)
    approved = await edge_client.post(f"/api/v1/scenarios/{scenario_id}/approve")
    command = await edge_client.post(f"/api/v1/scenarios/{scenario_id}/apply", json={})
    assert approved.json()["status"] == "APPROVED"
    assert command.json()["status"] == "PENDING"
    operation_id = command.json()["operation_id"]

    headers = {"Authorization": f"Bearer {EDGE_SECRET}"}
    leased = await edge_client.get(
        "/internal/v1/commands/next", params={"bridge_id": "edge-main"}, headers=headers
    )
    identity = {
        "operation_id": operation_id,
        "attempt_number": 1,
        "bridge_id": "edge-main",
    }
    acknowledged = await edge_client.post(
        "/internal/v1/commands/ack", json=identity, headers=headers
    )
    before_result = await edge_client.get(f"/api/v1/scenarios/{scenario_id}")
    completed = await edge_client.post(
        "/internal/v1/commands/result",
        json={**identity, "status": "COMPLETED", "detail": "applied"},
        headers=headers,
    )
    after_result = await edge_client.get(f"/api/v1/scenarios/{scenario_id}")

    assert leased.json()["operation_id"] == operation_id
    assert acknowledged.json()["status"] == "ACKNOWLEDGED"
    assert before_result.json()["status"] == "APPROVED"
    assert completed.json()["status"] == "COMPLETED"
    assert after_result.json()["status"] == "APPLIED"


@pytest.mark.asyncio
async def test_transport_task_command_edge_ack_and_completion(edge_client: AsyncClient) -> None:
    command = await edge_client.post(
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
    operation_id = command.json()["operation_id"]
    headers = {"Authorization": f"Bearer {EDGE_SECRET}"}
    leased = await edge_client.get(
        "/internal/v1/commands/next", params={"bridge_id": "edge-main"}, headers=headers
    )
    identity = {
        "operation_id": operation_id,
        "attempt_number": 1,
        "bridge_id": "edge-main",
    }
    acknowledged = await edge_client.post(
        "/internal/v1/commands/ack", json=identity, headers=headers
    )
    completed = await edge_client.post(
        "/internal/v1/commands/result",
        json={**identity, "status": "COMPLETED", "detail": "task accepted"},
        headers=headers,
    )

    assert command.status_code == 202
    assert leased.json()["command_type"] == "CREATE_TRANSPORT_TASK"
    assert leased.json()["task_id"] == "TASK-LOCAL-0001"
    assert acknowledged.json()["status"] == "ACKNOWLEDGED"
    assert completed.json()["status"] == "COMPLETED"
