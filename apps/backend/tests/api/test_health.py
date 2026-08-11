import pytest
from ev_twin_api.api.health import HealthResponse
from ev_twin_api.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200

    body = HealthResponse.model_validate(response.json())
    assert body.status == "ok"
