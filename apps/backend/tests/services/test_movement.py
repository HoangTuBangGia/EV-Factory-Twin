import math

import pytest
from ev_twin_api.core.layout import FACTORY_HEIGHT_M, FACTORY_WIDTH_M
from ev_twin_api.core.routes import ROUTES
from ev_twin_api.schemas.robot import Pose
from ev_twin_api.services.movement import RouteProgress, advance_along_route

ROUTE_KEY = ("BATTERY_BUFFER", "MARRIAGE_STATION")
SPEED_MPS = 1.2
DT = 0.1


def _run_route(start: Pose, speed: float = SPEED_MPS, dt: float = DT) -> list[Pose]:
    progress = RouteProgress(route_key=ROUTE_KEY)
    pose = start
    poses = [pose]
    finished = False
    ticks = 0
    while not finished and ticks < 10_000:
        pose, _velocity, finished = advance_along_route(pose, progress, speed, dt)
        poses.append(pose)
        ticks += 1
    return poses


def test_position_changes_over_time_while_moving() -> None:
    progress = RouteProgress(route_key=ROUTE_KEY)
    start = Pose(x=5.0, y=12.0, yaw=0.0)

    new_pose, _velocity, _finished = advance_along_route(start, progress, SPEED_MPS, DT)

    assert (new_pose.x, new_pose.y) != (start.x, start.y)


def test_yaw_changes_when_heading_changes() -> None:
    progress_leg_1 = RouteProgress(route_key=ROUTE_KEY, waypoint_index=1)
    pose_leg_1, _velocity, _finished = advance_along_route(
        Pose(x=2.0, y=4.0, yaw=0.0), progress_leg_1, SPEED_MPS, DT
    )
    # heading toward waypoint 1 (8,4) from (2,4): dx=6, dy=0
    assert pose_leg_1.yaw == pytest.approx(0.0)

    progress_leg_2 = RouteProgress(route_key=ROUTE_KEY, waypoint_index=2)
    pose_leg_2, _velocity2, _finished2 = advance_along_route(
        Pose(x=8.0, y=4.0, yaw=0.0), progress_leg_2, SPEED_MPS, DT
    )
    # heading toward waypoint 2 (12,8) from (8,4): dx=4, dy=4 -> different heading
    assert pose_leg_2.yaw == pytest.approx(math.atan2(4.0, 4.0))
    assert pose_leg_2.yaw != pytest.approx(pose_leg_1.yaw)


def test_velocity_reflects_motion_while_moving() -> None:
    progress = RouteProgress(route_key=ROUTE_KEY)
    start = Pose(x=5.0, y=12.0, yaw=0.0)

    _pose, velocity, finished = advance_along_route(start, progress, SPEED_MPS, DT)

    assert finished is False
    assert velocity.linear == pytest.approx(SPEED_MPS)


def test_velocity_is_zero_once_route_is_finished() -> None:
    progress = RouteProgress(route_key=ROUTE_KEY, waypoint_index=len(ROUTES[ROUTE_KEY]))
    pose = Pose(x=16.0, y=8.0, yaw=0.0)

    _pose, velocity, finished = advance_along_route(pose, progress, SPEED_MPS, DT)

    assert finished is True
    assert velocity.linear == 0.0


def test_robot_visits_waypoints_in_order_without_skipping() -> None:
    start = Pose(x=2.0, y=4.0, yaw=0.0)
    poses = _run_route(start)
    visited = [(round(p.x, 6), round(p.y, 6)) for p in poses]

    for waypoint in ROUTES[ROUTE_KEY]:
        assert waypoint in visited

    visit_order = [visited.index(waypoint) for waypoint in ROUTES[ROUTE_KEY]]
    assert visit_order == sorted(visit_order)


def test_large_dt_still_advances_one_waypoint_at_a_time_without_skipping() -> None:
    # a huge per-call distance budget (well past any single segment length)
    # must still stop exactly at each waypoint in turn, not skip ahead.
    start = Pose(x=2.0, y=4.0, yaw=0.0)
    poses = _run_route(start, speed=3.0, dt=5.0)
    visited = [(round(p.x, 6), round(p.y, 6)) for p in poses]

    for waypoint in ROUTES[ROUTE_KEY]:
        assert waypoint in visited
    visit_order = [visited.index(waypoint) for waypoint in ROUTES[ROUTE_KEY]]
    assert visit_order == sorted(visit_order)


def test_positions_stay_within_factory_bounds() -> None:
    start = Pose(x=5.0, y=12.0, yaw=0.0)
    poses = _run_route(start)

    for pose in poses:
        assert 0 <= pose.x <= FACTORY_WIDTH_M
        assert 0 <= pose.y <= FACTORY_HEIGHT_M


def test_movement_is_deterministic() -> None:
    start = Pose(x=5.0, y=12.0, yaw=0.0)
    poses_a = _run_route(start)
    poses_b = _run_route(start)

    assert [(p.x, p.y, p.yaw) for p in poses_a] == [(p.x, p.y, p.yaw) for p in poses_b]
