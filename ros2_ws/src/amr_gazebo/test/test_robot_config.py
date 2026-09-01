import importlib.util
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

LAUNCH_FILE = Path(__file__).parents[1] / "launch" / "sim.launch.py"
SPEC = importlib.util.spec_from_file_location("amr_sim_launch", LAUNCH_FILE)
assert SPEC is not None and SPEC.loader is not None
SIM_LAUNCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SIM_LAUNCH)


def robot(robot_id: str, namespace: str, y: float) -> dict[str, str | float]:
    return {
        "robot_id": robot_id,
        "namespace": namespace,
        "x": 0.0,
        "y": y,
        "z": 0.2,
        "yaw": 0.0,
    }


def write_config(tmp_path: Path, robots: list[dict[str, str | float]]) -> Path:
    path = tmp_path / "robots.json"
    path.write_text(json.dumps({"robots": robots}), encoding="utf-8")
    return path


def test_default_config_has_two_unique_namespaced_spawn_poses() -> None:
    robots = SIM_LAUNCH.load_robot_config(Path(__file__).parents[1] / "config" / "robots.json")

    assert [entry["robot_id"] for entry in robots] == ["AMR-01", "AMR-02"]
    assert [entry["namespace"] for entry in robots] == ["amr_01", "amr_02"]
    assert {(entry["x"], entry["y"], entry["yaw"]) for entry in robots} == {
        (31.0, 13.0, 0.0),
        (33.0, 13.0, 0.0),
    }


def test_world_covers_canonical_footprint_and_models_the_no_go_obstacle() -> None:
    root = ET.parse(Path(__file__).parents[1] / "worlds" / "amr_test.sdf").getroot()
    models = {model.attrib["name"]: model for model in root.findall("./world/model")}

    floor_size = models["factory_floor"].findtext(
        "./link/visual/geometry/plane/size"
    )

    assert floor_size == "120 40"
    assert {
        "north_boundary",
        "south_boundary",
        "west_boundary",
        "east_boundary",
        "giga_press_obstacle",
    } <= models.keys()


@pytest.mark.parametrize(
    ("robots", "message"),
    [
        ([robot("AMR-01", "amr_01", 0.0)], "at least two"),
        (
            [robot("AMR-01", "amr_01", 0.0), robot("AMR-01", "amr_02", 1.0)],
            "duplicate robot_id",
        ),
        (
            [robot("AMR-01", "amr_01", 0.0), robot("AMR-02", "amr_01", 1.0)],
            "duplicate namespace",
        ),
        (
            [robot("AMR-01", "amr_01", 0.0), robot("AMR-02", "AMR 02", 1.0)],
            "namespace is invalid",
        ),
        (
            [robot("AMR-01", "amr_01", 0.0), robot("AMR-02", "amr_02", float("nan"))],
            "must be finite",
        ),
    ],
)
def test_invalid_fleet_config_fails_before_launch(tmp_path: Path, robots, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        SIM_LAUNCH.load_robot_config(write_config(tmp_path, robots))
