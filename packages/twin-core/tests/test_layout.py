import pytest
from pydantic import ValidationError
from twin_core.default_layout import default_layout_content
from twin_core.models.layout import LayoutVersionContent


def test_canonical_layout_matches_full_factory_footprint() -> None:
    layout = default_layout_content()

    assert (layout.width, layout.height) == (120, 40)
    assert layout.config.robot_count == 5
    assert (
        layout.routes[0].waypoints[0].x,
        layout.routes[0].waypoints[0].y,
    ) == (layout.stations[0].x, layout.stations[0].y)


def valid_layout() -> dict[str, object]:
    return {
        "width": 20,
        "height": 15,
        "stations": [
            {"id": "BATTERY_BUFFER", "type": "BATTERY_BUFFER", "x": 2, "y": 4},
            {"id": "MARRIAGE_STATION", "type": "MARRIAGE_STATION", "x": 16, "y": 8},
            {"id": "CHARGING_STATION", "type": "CHARGING_STATION", "x": 2, "y": 12},
        ],
        "routes": [
            {
                "id": "BATTERY_DELIVERY",
                "start_station_id": "BATTERY_BUFFER",
                "end_station_id": "MARRIAGE_STATION",
                "waypoints": [{"x": 2, "y": 4}, {"x": 8, "y": 4}, {"x": 16, "y": 8}],
            }
        ],
        "no_go_zones": [
            {
                "id": "NO_GO_01",
                "points": [
                    {"x": 8, "y": 10},
                    {"x": 12, "y": 10},
                    {"x": 12, "y": 13},
                    {"x": 8, "y": 13},
                ],
            }
        ],
        "congestion_zones": [],
        "config": {
            "robot_count": 2,
            "demand_interval_seconds": 8,
            "robot_speed_mps": 1,
            "charger_count": 1,
        },
    }


def test_valid_layout_contract() -> None:
    layout = LayoutVersionContent.model_validate(valid_layout())

    assert layout.config.robot_count == 2
    assert layout.routes[0].start_station_id == "BATTERY_BUFFER"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["stations"].__setitem__(0, {**value["stations"][0], "x": 21}),
        lambda value: value["routes"][0].__setitem__("end_station_id", "UNKNOWN"),
        lambda value: value["routes"][0]["waypoints"].__setitem__(-1, {"x": 15, "y": 8}),
        lambda value: value["no_go_zones"][0].__setitem__(
            "points",
            [{"x": 8, "y": 10}, {"x": 12, "y": 13}, {"x": 12, "y": 10}, {"x": 8, "y": 13}],
        ),
    ],
)
def test_rejects_invalid_geometry_and_route(mutate) -> None:
    payload = valid_layout()
    mutate(payload)

    with pytest.raises(ValidationError):
        LayoutVersionContent.model_validate(payload)


def test_rejects_route_crossing_no_go_zone() -> None:
    payload = valid_layout()
    payload["no_go_zones"] = [
        {
            "id": "BLOCK_ROUTE",
            "points": [
                {"x": 6, "y": 3},
                {"x": 7, "y": 3},
                {"x": 7, "y": 5},
                {"x": 6, "y": 5},
            ],
        }
    ]

    with pytest.raises(ValidationError, match="crosses no-go zone"):
        LayoutVersionContent.model_validate(payload)
