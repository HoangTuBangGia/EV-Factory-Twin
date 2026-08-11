import pytest
from ev_twin_api.schemas.metrics import FactoryMetrics
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_metrics_returns_valid_schema(client: AsyncClient) -> None:
    response = await client.get("/api/v1/metrics")

    assert response.status_code == 200
    metrics = FactoryMetrics.model_validate(response.json())
    assert metrics.completed_tasks == 0
    assert metrics.queued_tasks == 0
