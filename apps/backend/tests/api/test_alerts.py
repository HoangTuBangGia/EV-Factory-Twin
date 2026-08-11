import pytest
from ev_twin_api.schemas.alert import FactoryAlert
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_alerts_returns_valid_schema(client: AsyncClient) -> None:
    response = await client.get("/api/v1/alerts")

    assert response.status_code == 200
    alerts = [FactoryAlert.model_validate(item) for item in response.json()]
    assert alerts == []
