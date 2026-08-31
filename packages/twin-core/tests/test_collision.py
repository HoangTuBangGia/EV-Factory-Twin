import pytest
from twin_core.collision import AMR_COLLISION_DISTANCE_M, colliding_robot_pairs


def test_collision_pairs_are_stable_and_use_footprint_distance() -> None:
    positions = {"AMR-02": (0.4, 0.0), "AMR-01": (0.0, 0.0), "AMR-03": (5.0, 5.0)}
    assert colliding_robot_pairs(positions) == {("AMR-01", "AMR-02")}
    assert AMR_COLLISION_DISTANCE_M > 0.65


def test_collision_distance_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        colliding_robot_pairs({}, collision_distance_m=0.0)
    with pytest.raises(ValueError, match="finite"):
        colliding_robot_pairs({}, collision_distance_m=float("nan"))
