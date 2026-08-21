import json

import pytest
from fleet_manager.node import RobotRecord, load_robot_records, select_robot


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
