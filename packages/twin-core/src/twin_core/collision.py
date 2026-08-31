from collections.abc import Mapping
from itertools import combinations
from math import hypot, isfinite

AMR_FOOTPRINT_LENGTH_M = 0.65
AMR_FOOTPRINT_WIDTH_M = 0.48
AMR_COLLISION_DISTANCE_M = hypot(AMR_FOOTPRINT_LENGTH_M, AMR_FOOTPRINT_WIDTH_M)


def colliding_robot_pairs(
    positions: Mapping[str, tuple[float, float]],
    *,
    collision_distance_m: float = AMR_COLLISION_DISTANCE_M,
) -> set[tuple[str, str]]:
    """Return stable robot-ID pairs whose conservative footprint circles overlap."""
    if not isfinite(collision_distance_m) or collision_distance_m <= 0.0:
        raise ValueError("collision_distance_m must be positive and finite")
    return {
        (left_id, right_id)
        for (left_id, left), (right_id, right) in combinations(sorted(positions.items()), 2)
        if hypot(left[0] - right[0], left[1] - right[1]) <= collision_distance_m
    }
