# Multi-AMR Gazebo Foundation

## Summary

Changed the Gazebo launch from one hard-coded AMR to a validated, configurable
fleet with two robots by default and isolated ROS namespaces.

## Motivation

The live MVP acceptance path requires at least two AMRs before navigation, task
assignment or bidirectional commands can be implemented safely.

## Architecture / Contract Impact

- `robots.json` is the edge spawn source for robot ID, namespace and pose.
- Gazebo runs once and `/clock` is bridged once.
- Every AMR owns a robot-state publisher and `cmd_vel`, `odom`, `tf`, `tf_static`.
- The launch rejects fewer than two robots, invalid/duplicate identity and invalid pose.
- Navigation, battery/status simulation and Fleet Manager remain later checkpoints.

## Files Changed

- `ros2_ws/src/amr_gazebo/config/robots.json`
- `ros2_ws/src/amr_gazebo/launch/sim.launch.py`
- AMR Gazebo tests/package installation metadata
- ROS development and architecture documentation

## Verification

See the checkpoint handoff for `ros-check` results. Tests validate distinct spawn
configuration, observe two odom/TF trees, command only AMR-01 and check AMR-02
remains stationary.

## CI / Build Impact

The existing ROS CI package list and `make ros-check` remain authoritative. No
new runtime dependency was introduced.

## Follow-up

Implement deterministic station-to-station navigation and the robot-state simulator.
