from functools import partial

import pytest
from conftest import make_test_user
from ev_twin_api.api.dependencies import get_current_user
from ev_twin_api.main import app
from ev_twin_api.schemas.auth import AppRole
from httpx2 import AsyncClient


def layout_payload(name: str = "Candidate layout") -> dict[str, object]:
    return {
        "name": name,
        "content": {
            "width": 20,
            "height": 15,
            "stations": [
                {"id": "BATTERY_BUFFER", "type": "BATTERY_BUFFER", "x": 2, "y": 4},
                {
                    "id": "MARRIAGE_STATION",
                    "type": "MARRIAGE_STATION",
                    "x": 16,
                    "y": 8,
                },
                {
                    "id": "CHARGING_STATION",
                    "type": "CHARGING_STATION",
                    "x": 2,
                    "y": 12,
                },
            ],
            "routes": [
                {
                    "id": "BATTERY_DELIVERY",
                    "start_station_id": "BATTERY_BUFFER",
                    "end_station_id": "MARRIAGE_STATION",
                    "waypoints": [
                        {"x": 2, "y": 4},
                        {"x": 8, "y": 4},
                        {"x": 16, "y": 8},
                    ],
                }
            ],
            "no_go_zones": [],
            "congestion_zones": [
                {
                    "id": "CONGESTION_01",
                    "delay_multiplier": 1.25,
                    "points": [
                        {"x": 10, "y": 10},
                        {"x": 12, "y": 10},
                        {"x": 12, "y": 12},
                    ],
                }
            ],
            "config": {
                "robot_count": 2,
                "demand_interval_seconds": 8,
                "robot_speed_mps": 1,
                "charger_count": 1,
            },
        },
    }


def use_role(role: AppRole) -> None:
    app.dependency_overrides[get_current_user] = partial(make_test_user, role)


@pytest.mark.asyncio
async def test_layout_crud_and_immutable_versions(client: AsyncClient) -> None:
    use_role(AppRole.DESIGNER)
    created = await client.post("/api/v1/layouts", json=layout_payload())
    assert created.status_code == 201
    layout_id = created.json()["layout_id"]
    assert created.json()["version"] == 1

    renamed = await client.patch(f"/api/v1/layouts/{layout_id}", json={"name": "Renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed"

    content = layout_payload()["content"]
    content["config"]["robot_count"] = 3
    second = await client.post(f"/api/v1/layouts/{layout_id}/versions", json={"content": content})
    assert second.status_code == 201
    assert second.json()["version"] == 2

    first = await client.get(f"/api/v1/layouts/{layout_id}/versions/1")
    latest = await client.get(f"/api/v1/layouts/{layout_id}")
    assert first.json()["config"]["robot_count"] == 2
    assert latest.json()["config"]["robot_count"] == 3

    archived = await client.delete(f"/api/v1/layouts/{layout_id}")
    listing = await client.get("/api/v1/layouts")
    conflict = await client.post(f"/api/v1/layouts/{layout_id}/versions", json={"content": content})
    assert archived.status_code == 204
    assert [layout["id"] for layout in listing.json()] == ["LAYOUT-DEFAULT"]
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_monitor_can_read_but_not_mutate_layouts(client: AsyncClient) -> None:
    use_role(AppRole.MONITOR)

    assert (await client.get("/api/v1/layouts")).status_code == 200
    assert (await client.post("/api/v1/layouts", json=layout_payload())).status_code == 403


@pytest.mark.asyncio
async def test_layout_validation_rejects_route_crossing_no_go_zone(
    client: AsyncClient,
) -> None:
    use_role(AppRole.DESIGNER)
    payload = layout_payload()
    payload["content"]["no_go_zones"] = [
        {
            "id": "BLOCK_ROUTE",
            "points": [
                {"x": 6, "y": 3},
                {"x": 9, "y": 3},
                {"x": 9, "y": 5},
                {"x": 6, "y": 5},
            ],
        }
    ]

    response = await client.post("/api/v1/layouts", json=payload)

    assert response.status_code == 422
