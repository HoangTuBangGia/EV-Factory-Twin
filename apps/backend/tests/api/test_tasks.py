import pytest
from ev_twin_api.schemas.task import Task
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_tasks_returns_valid_schema(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tasks")

    assert response.status_code == 200
    tasks = [Task.model_validate(item) for item in response.json()]
    assert tasks == []


@pytest.mark.asyncio
async def test_get_unknown_task_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tasks/TASK-9999")

    assert response.status_code == 404
    assert response.json() != {}
