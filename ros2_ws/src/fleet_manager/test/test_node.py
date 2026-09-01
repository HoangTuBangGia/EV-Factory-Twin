import json

import pytest
from fleet_manager.node import (
    RobotRecord,
    load_robot_records,
    runtime_config_error,
    select_charging_robots,
    select_robot,
)


def test_load_robot_records_rejects_duplicate_namespace(tmp_path) -> None:
    config = tmp_path / "robots.json"
    config.write_text(
        json.dumps(
            {
                "robots": [
                    {"robot_id": "AMR-01", "namespace": "amr"},
                    {"robot_id": "AMR-02", "namespace": "amr"},
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unique"):
        load_robot_records(config)


def test_select_robot_uses_nearest_eligible_robot_and_stable_id_tie_break() -> None:
    robots = [
        RobotRecord("AMR-02", "amr_02", "IDLE", 0.8, 1.0, 0.0),
        RobotRecord("AMR-01", "amr_01", "IDLE", 0.8, -1.0, 0.0),
        RobotRecord("AMR-03", "amr_03", "ERROR", 0.9, 0.0, 0.0),
    ]
    assert select_robot(robots, (0.0, 0.0), 0.2).robot_id == "AMR-01"


def test_select_robot_excludes_low_battery_and_busy_robot() -> None:
    robots = [
        RobotRecord("AMR-01", "amr_01", "IDLE", 0.2, 0.0, 0.0),
        RobotRecord("AMR-02", "amr_02", "IDLE", 0.8, 0.0, 0.0, "TASK-1"),
    ]
    assert select_robot(robots, (0.0, 0.0), 0.2) is None


def test_select_robot_excludes_robot_without_odometry() -> None:
    robot = RobotRecord("AMR-01", "amr_01", status="IDLE", battery=0.8)
    assert select_robot([robot], (0.0, 0.0), 0.2) is None


def test_low_battery_charging_selection_respects_ownership_and_capacity() -> None:
    robots = [
        RobotRecord("AMR-01", "amr_01", "IDLE", 0.1, 0.0, 0.0),
        RobotRecord("AMR-02", "amr_02", "IDLE", 0.2, 0.0, 0.0),
        RobotRecord("AMR-03", "amr_03", "IDLE", 0.05, 0.0, 0.0, "TASK-1"),
        RobotRecord("AMR-04", "amr_04", "MOVING", 0.05, 0.0, 0.0),
    ]

    selected = select_charging_robots(robots, threshold=0.3, capacity=1)

    assert [robot.robot_id for robot in selected] == ["AMR-01"]
    assert select_charging_robots(robots, threshold=0.3, capacity=0) == []


def test_runtime_apply_rejects_topology_change_requiring_relaunch() -> None:
    request = type(
        "Request",
        (),
        {
            "robot_count": 3,
            "robot_speed_mps": 1.0,
            "charger_count": 1,
            "demand_interval_seconds": 8.0,
            "layout_id": "LAYOUT-DEFAULT",
            "layout_version": 3,
            "route_id": "BATTERY_DELIVERY",
        },
    )()
    assert "robot_count" in runtime_config_error(
        request,
        robot_count=2,
        chargers=1,
        demand=8.0,
        layout_id="LAYOUT-DEFAULT",
        layout_version=3,
        route_id="BATTERY_DELIVERY",
    )


def test_runtime_apply_allows_live_speed_change() -> None:
    request = type(
        "Request",
        (),
        {
            "robot_count": 2,
            "robot_speed_mps": 2.5,
            "charger_count": 1,
            "demand_interval_seconds": 8.0,
            "layout_id": "LAYOUT-DEFAULT",
            "layout_version": 3,
            "route_id": "BATTERY_DELIVERY",
        },
    )()
    assert (
        runtime_config_error(
            request,
            robot_count=2,
            chargers=1,
            demand=8.0,
            layout_id="LAYOUT-DEFAULT",
            layout_version=3,
            route_id="BATTERY_DELIVERY",
        )
        is None
    )
