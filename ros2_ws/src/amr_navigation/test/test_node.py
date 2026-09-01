import json
import math
from pathlib import Path

import pytest
from amr_navigation.config import load_navigation_config, load_stations
from amr_navigation.node import (
    STATUSES,
    navigation_speed_error,
    next_battery,
    normalize_angle,
)


def test_station_config_is_finite_and_keyed_by_station_id(tmp_path) -> None:
    config = tmp_path / "stations.json"
    config.write_text(
        json.dumps({"stations": {"BATTERY_BUFFER": {"x": 2, "y": 4}}}),
        encoding="utf-8",
    )

    assert load_stations(config) == {"BATTERY_BUFFER": (2.0, 4.0)}


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_station_config_rejects_non_finite_coordinates(tmp_path, value: float) -> None:
    config = tmp_path / "stations.json"
    config.write_text(
        json.dumps({"stations": {"BAD": {"x": value, "y": 0}}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must be finite"):
        load_stations(config)


def test_angle_normalization_uses_shortest_turn() -> None:
    assert math.isclose(normalize_angle(3 * math.pi), math.pi)
    assert math.isclose(normalize_angle(-3 * math.pi), -math.pi)


def test_battery_drains_moves_charges_and_stays_bounded() -> None:
    assert next_battery(0.5, "MOVING", 10.0, 0.005, 0.05) == 0.45
    assert next_battery(0.5, "DELIVERING", 10.0, 0.005, 0.05) == 0.45
    assert next_battery(0.5, "CHARGING", 10.0, 0.005, 0.05) == 1.0
    assert next_battery(0.01, "MOVING", 10.0, 0.005, 0.05) == 0.0
    assert next_battery(0.5, "IDLE", 10.0, 0.005, 0.05) == 0.5


def test_state_simulator_supports_the_mvp_status_contract() -> None:
    assert {
        "IDLE",
        "MOVING",
        "PICKING",
        "DELIVERING",
        "CHARGING",
        "ERROR",
        "OFFLINE",
    } == STATUSES


def test_navigation_speed_validation_matches_scenario_contract() -> None:
    assert navigation_speed_error(2.5) is None
    assert navigation_speed_error(0.0) is not None
    assert navigation_speed_error(float("nan")) is not None


def test_default_ros_layout_matches_the_canonical_runtime_contract() -> None:
    loaded = load_navigation_config(Path(__file__).parents[1] / "config" / "stations.json")

    assert (loaded.layout_id, loaded.layout_version, loaded.width, loaded.height) == (
        "LAYOUT-DEFAULT",
        3,
        120.0,
        40.0,
    )
    assert loaded.station_positions() == {
        "BATTERY_BUFFER": (32.0, 29.0),
        "MARRIAGE_STATION": (52.0, 6.0),
        "MARRIAGE_STATION_2": (82.0, 8.0),
        "CHARGING_STATION": (32.0, 11.0),
    }
    assert set(loaded.routes) == {
        "BATTERY_DELIVERY",
        "BATTERY_DELIVERY_LONG",
        "CHARGER_LINK",
    }


def test_configured_station_type_controls_arrival_without_hard_coded_ids(tmp_path) -> None:
    config = tmp_path / "stations.json"
    config.write_text(
        json.dumps(
            {
                "stations": {
                    "BUFFER_2": {"type": "BATTERY_BUFFER", "x": 2, "y": 4},
                    "LINE_2": {"type": "MARRIAGE_STATION", "x": 4, "y": 4},
                    "CHARGER_2": {"type": "CHARGING_STATION", "x": 2, "y": 2},
                    "INSPECTION": {"type": "WAYPOINT", "x": 3, "y": 3},
                }
            }
        ),
        encoding="utf-8",
    )

    loaded = load_navigation_config(config)

    assert loaded.stations["BUFFER_2"].arrival_status == "PICKING"
    assert loaded.stations["LINE_2"].arrival_status == "IDLE"
    assert loaded.stations["CHARGER_2"].arrival_status == "CHARGING"
    assert loaded.stations["INSPECTION"].arrival_status == "IDLE"


def test_navigation_uses_configured_route_network_for_pickup_and_charging(tmp_path) -> None:
    config = tmp_path / "stations.json"
    config.write_text(
        json.dumps(
            {
                "width": 20,
                "height": 20,
                "stations": {
                    "BUFFER": {"type": "BATTERY_BUFFER", "x": 0, "y": 0},
                    "LINE": {"type": "MARRIAGE_STATION", "x": 10, "y": 0},
                    "CHARGER": {"type": "CHARGING_STATION", "x": 0, "y": 10},
                },
                "routes": [
                    {
                        "id": "DELIVERY",
                        "start_station_id": "BUFFER",
                        "end_station_id": "LINE",
                        "waypoints": [
                            {"x": 0, "y": 0},
                            {"x": 5, "y": 2},
                            {"x": 10, "y": 0},
                        ],
                    },
                    {
                        "id": "CHARGER_LINK",
                        "start_station_id": "CHARGER",
                        "end_station_id": "BUFFER",
                        "waypoints": [{"x": 0, "y": 10}, {"x": 0, "y": 0}],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    loaded = load_navigation_config(config)

    assert loaded.path_to((0, 9), "LINE") == (
        (0.0, 10.0),
        (0.0, 0.0),
        (5.0, 2.0),
        (10.0, 0.0),
    )
    assert loaded.path_to((0, 0), "LINE", "DELIVERY") == (
        (0.0, 0.0),
        (5.0, 2.0),
        (10.0, 0.0),
    )


def test_config_rejects_route_that_crosses_no_go_zone(tmp_path) -> None:
    config = tmp_path / "stations.json"
    config.write_text(
        json.dumps(
            {
                "width": 10,
                "height": 10,
                "stations": {
                    "A": {"x": 0, "y": 5},
                    "B": {"x": 10, "y": 5},
                },
                "routes": [
                    {
                        "id": "BLOCKED",
                        "start_station_id": "A",
                        "end_station_id": "B",
                        "waypoints": [{"x": 0, "y": 5}, {"x": 10, "y": 5}],
                    }
                ],
                "no_go_zones": [
                    {
                        "id": "NO_GO",
                        "points": [
                            {"x": 4, "y": 4},
                            {"x": 6, "y": 4},
                            {"x": 6, "y": 6},
                            {"x": 4, "y": 6},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="crosses a no-go zone"):
        load_navigation_config(config)
