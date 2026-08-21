# Simulated Navigation and Robot State

## Summary

Added a typed ROS 2 station-navigation action and one deterministic navigation/
state simulator per AMR. Robots publish battery, status, task and payload state.

## Motivation

Fleet Manager needs a stable goal/result boundary before task assignment can be
implemented. The MVP needs repeatable motion and state behavior, not advanced
path planning or collision physics.

## Architecture / Contract Impact

- `amr_interfaces/NavigateToStation` defines goal, feedback and result.
- Results are `SUCCESS`, `FAILED` or `TIMED_OUT`.
- Each robot owns a namespaced action, state topics, odom input and cmd_vel output.
- Station goals and Gazebo odometry use the same world coordinate frame.
- Gazebo uses planar `VelocityControl` and `OdometryPublisher` in a zero-gravity
  world; collision and wheel-contact physics remain outside the MVP.
- Battery drains while moving/delivering and increases while charging.
- The ROS state contract supports IDLE, MOVING, PICKING, DELIVERING, CHARGING,
  ERROR and OFFLINE. Existing detailed MOCK statuses remain compatibility values.

## Files Changed

Added `amr_interfaces` and `amr_navigation`; updated the Gazebo fleet launch,
canonical status contract, tests and ROS documentation.

## Verification

See checkpoint handoff. Unit tests cover station validation, angle control,
battery behavior and status coverage. Headless Gazebo tests exercise success,
failed and timeout action results plus namespaced state isolation.

## CI / Build Impact

ROS CI discovers the two new packages through the workspace. The workflow package
allowlist must include them. No host/runtime dependency outside ROS Jazzy was added.

## Follow-up

Build Fleet Manager and Task Manager clients on the typed action contract.
