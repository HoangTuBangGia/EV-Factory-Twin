# Headless Gazebo Launch Test

## Summary

The Gazebo launch test now runs Gazebo server-only, avoiding GUI startup in GitHub Actions.

## Motivation

GitHub Actions runners do not provide an X11 display, so Gazebo GUI aborted with the Qt `xcb` platform error.

## Architecture / Contract Impact

The simulation launch file accepts a `gz_args` launch argument. Its default remains `-r`; the launch test overrides it with `-s -r`.

## Files Changed

- `ros2_ws/src/amr_gazebo/launch/sim.launch.py`
- `ros2_ws/src/amr_gazebo/test/test_sim_launch.py`

## Verification

`colcon test --event-handlers=console_direct+ --packages-select amr_gazebo` passed locally (1/1 test).

## CI / Build Impact

The `amr_gazebo` launch test no longer requires a display server.

## Follow-up

Re-run the ROS GitHub Actions workflow.
