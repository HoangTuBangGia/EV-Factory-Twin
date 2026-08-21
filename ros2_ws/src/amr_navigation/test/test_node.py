import json
import math

import pytest

from amr_navigation.node import STATUSES, load_stations, next_battery, normalize_angle


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
    assert STATUSES == {
        "IDLE",
        "MOVING",
        "PICKING",
        "DELIVERING",
        "CHARGING",
        "ERROR",
        "OFFLINE",
    }
