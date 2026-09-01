# Align ROS Factory Coordinates

## Summary

Aligned Gazebo AMR spawn poses and ROS navigation stations with the canonical
120 × 40 m factory coordinate frame.

## Motivation

ROS previously spawned robots around `(0, 0)` and navigated to prototype station
coordinates, causing live telemetry-driven AMRs to render outside or away from
their stations in the frontend map.

## Architecture / Contract Impact

MOCK, ROS and frontend layout geometry now use the same factory-metre coordinate
frame. Custom station configuration is resolved inside the launch context before
being passed to navigation and fleet nodes.

## Files Changed

- Updated default Gazebo AMR spawn poses.
- Updated canonical ROS navigation station coordinates.
- Updated ROS launch argument resolution and related launch-test fixtures.
- Added odometry settling synchronization to the multi-AMR isolation test.

## Verification

`make ros-check` passed in the ROS 2 Jazzy Distrobox environment.

## CI / Build Impact

The existing ROS CI workflow verifies all affected packages; no dependency or
workflow change is required.

## Follow-up

None.
