import pytest
from ev_twin_api.schemas.factory import FactoryLayout
from httpx2 import AsyncClient


@pytest.mark.asyncio
async def test_get_factory_returns_valid_layout(client: AsyncClient) -> None:
    response = await client.get("/api/v1/factory")

    assert response.status_code == 200

    layout = FactoryLayout.model_validate(response.json())
    assert layout.width_m == 20
    assert layout.height_m == 15
    assert len(layout.stations) == 6
    assert {station.id for station in layout.stations} == {
        "BATTERY_BUFFER",
        "INTERSECTION_A",
        "INTERSECTION_B",
        "MARRIAGE_STATION",
        "CHARGING_STATION",
        "IDLE_ZONE",
    }
