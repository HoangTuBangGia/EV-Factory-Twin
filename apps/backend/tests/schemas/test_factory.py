import pytest
from ev_twin_api.schemas.factory import FactoryLayout, MockFactoryConfig, Station
from pydantic import ValidationError


def test_station_fields() -> None:
    station = Station(id="BATTERY_BUFFER", name="Battery Buffer", type="BUFFER", x=2, y=4)
    assert station.x == 2
    assert station.y == 4


def test_factory_layout_holds_stations() -> None:
    layout = FactoryLayout(
        width_m=20,
        height_m=15,
        stations=[Station(id="BATTERY_BUFFER", name="Battery Buffer", type="BUFFER", x=2, y=4)],
    )
    assert len(layout.stations) == 1


def test_mock_factory_config_defaults() -> None:
    config = MockFactoryConfig()
    assert config.robot_count == 5
    assert config.task_interval_seconds == 8.0
    assert config.robot_speed_mps == 1.2
    assert config.simulation_speed == 1.0
    assert config.low_battery_threshold == 20.0


@pytest.mark.parametrize("robot_count", [0, 11])
def test_mock_factory_config_robot_count_out_of_range_raises(robot_count: int) -> None:
    with pytest.raises(ValidationError):
        MockFactoryConfig(robot_count=robot_count)
