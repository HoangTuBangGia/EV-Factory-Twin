import pytest
from ev_twin_api.schemas.factory import FactoryLayout
from httpx2 import AsyncClient


@pytest.mark.asyncio
async def test_get_factory_returns_valid_layout(client: AsyncClient) -> None:
    response = await client.get("/api/v1/factory")

    assert response.status_code == 200

    layout = FactoryLayout.model_validate(response.json())
    assert layout.width_m == 120
    assert layout.height_m == 40
    assert len(layout.stations) == 4
    assert {station.id for station in layout.stations} == {
        "BATTERY_BUFFER",
        "MARRIAGE_STATION",
        "MARRIAGE_STATION_2",
        "CHARGING_STATION",
    }
