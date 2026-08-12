import asyncio

import pytest
from ev_twin_api.main import app
from ev_twin_api.schemas.task import Task
from httpx import AsyncClient


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
