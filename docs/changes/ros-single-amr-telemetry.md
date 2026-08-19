# ROS Single-AMR Telemetry Vertical Slice

## Summary

Added the first ROS 2 Jazzy/Gazebo Harmonic vertical slice: a differential-drive
AMR description, deterministic Gazebo launch/world, ROS-Gazebo bridges, and an
authenticated telemetry bridge to FastAPI.

## Motivation

The CORE live runtime needs a real robotics path before Nav2, fleet management,
replay, and multi-robot behavior are added.

## Architecture / Contract Impact

```text
Gazebo -> ROS 2 -> telemetry_bridge -> POST /internal/v1/telemetry
                                      -> /ws/factory -> browser
```

- `amr_description` owns Xacro, links, joints, inertial/collision data, and
  passive caster support.
- `amr_gazebo` owns the Harmonic world, spawn, DiffDrive, clock, odometry,
  velocity, and TF bridges.
- `telemetry_bridge` owns ROS odometry normalization and outbound HTTP only.
- Edge timestamps use host UTC, not Gazebo simulation time, because the backend
  stale guard uses UTC wall-clock state.
- The bridge reads `EDGE_TELEMETRY_SHARED_SECRET` from its environment only; it
  is never a ROS parameter.
- HTTP delivery uses one bounded latest-sample worker so ROS callbacks do not
  block on Render/backend outages.
- HTTP redirects are rejected so the bearer secret cannot be forwarded to a
  redirect target.
- DiffDrive owns `odom -> base_footprint`; `robot_state_publisher` uses simulation
  time and owns static descendants beginning with `base_footprint -> base_link`.
  Wheel transforms are deferred until real Gazebo joint states are bridged.

## Files Changed

Added ROS package manifests, CMake/setup metadata, Xacro, Gazebo world/launch,
telemetry bridge node/launch/tests, ROS Make targets, ROS CI, and this record.

## Verification

- Xacro expansion and URDF validation passed.
- `colcon build --symlink-install` passed for all three packages using temporary
  build/install/log directories.
- `colcon test` and `colcon test-result --verbose` passed: 20 tests, 0 failures.
- Headless Gazebo launch spawned the AMR and `/amr_01/odom` emitted a live sample
  with a connected `amr_01/odom -> amr_01/base_footprint -> amr_01/base_link`
  frame tree.
- ROS unit tests cover quaternion/UTC/strict JSON, URL/TLS policy, retries,
  redirect rejection, permanent HTTP failures, latest-sample bounds, and secret
  non-parameter policy. Package-integrated tests validate the expanded URDF and
  smoke-test live odometry, connected TF, and authenticated bridge HTTP delivery
  from the Gazebo launch. A shared fixture proves bridge serialization and backend
  ingestion use the same canonical payload.
- The backend integration test validates the real telemetry ingress, authenticated
  `/ws/factory` broadcast, and REST robot state using one canonical payload.
- Full Python `make check` passed with 393 tests; frontend lint/typecheck, 94 unit
  tests, and production build passed.

## CI / Build Impact

`.github/workflows/ros-ci.yml` uses the pinned `action-ros-ci` release with the
digest-pinned Ubuntu Noble prepared ROS environment. Local targets are `make ros-deps`,
`make ros-build`, `make ros-test`, and `make ros-check`.
The dependency gate verifies the installed `ament_python` colcon extension
directly and skips only that absent Noble rosdep mapping.

## Follow-up

Add Nav2 for the single AMR. A deployed Render smoke test remains an operational
release check. Battery producer, task/status producer, offline buffering,
multi-robot, and per-bridge identity are deferred.
