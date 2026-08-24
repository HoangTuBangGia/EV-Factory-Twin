import math
from dataclasses import dataclass

from ev_twin_api.schemas.robot import Pose, Velocity


@dataclass
class RouteProgress:
    """Tracks one robot's progress along an immutable waypoint snapshot.

    Internal engine bookkeeping only — not part of the FE-BE contract, so it
    intentionally does not live on the Robot schema.
    """

    waypoints: tuple[tuple[float, float], ...]
    waypoint_index: int = 0


def advance_along_route(
    pose: Pose, progress: RouteProgress, speed_mps: float, dt: float
) -> tuple[Pose, Velocity, bool]:
    """Move `pose` toward the current waypoint of an immutable route snapshot.

    A call advances at most one waypoint: overshoot past the target snaps
    exactly onto it (any leftover distance for that tick is discarded rather
    than spent on the next segment), so every waypoint is guaranteed to show
    up as an exact position at some tick boundary instead of only being
    passed through mid-tick. Returns (new_pose, new_velocity, route_finished).
    """
    waypoints = progress.waypoints

    if progress.waypoint_index >= len(waypoints):
        return pose, Velocity(linear=0.0, angular=0.0), True

    target_x, target_y = waypoints[progress.waypoint_index]
    dx, dy = target_x - pose.x, target_y - pose.y
    distance_to_target = math.hypot(dx, dy)
    distance_to_move = speed_mps * dt

    if distance_to_target <= distance_to_move:
        x, y = target_x, target_y
        yaw = math.atan2(dy, dx) if distance_to_target > 0 else pose.yaw
        progress.waypoint_index += 1
    else:
        yaw = math.atan2(dy, dx)
        ratio = distance_to_move / distance_to_target
        x = pose.x + dx * ratio
        y = pose.y + dy * ratio

    route_finished = progress.waypoint_index >= len(waypoints)
    velocity = Velocity(linear=0.0 if route_finished else speed_mps, angular=0.0)
    return Pose(x=x, y=y, yaw=yaw), velocity, route_finished
