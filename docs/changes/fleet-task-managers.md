# Fleet and Task Managers

## Summary

Added typed ROS 2 Fleet Manager and Task Manager nodes for queued battery
transport, robot assignment and bounded execution retry.

## Motivation

M2 exposed independent station navigation actions but did not coordinate robots
or own the transport-task lifecycle required by the Backend.

## Architecture / Contract Impact

- `CreateTransportTask` provides immediate acceptance acknowledgement.
- `ExecuteTransportTask` separates task scheduling from fleet execution.
- `TaskState` publishes the canonical lifecycle on `/fleet/task_updates`.
- Fleet selection requires `IDLE`, no active task, battery above threshold and
  chooses the nearest robot with a stable robot-ID tie break.
- Task execution calls pickup and dropoff navigation sequentially.
- New task flows use `QUEUED → ASSIGNED → PICKUP → DELIVERING → COMPLETED`.
  `FAILED` and `TIMED_OUT` may retry within a bounded budget.
- Backend continues to read legacy `IN_PROGRESS` and `DELIVERED` values but no
  longer emits them for new MOCK tasks.

## Files Changed

Added `fleet_manager`, `task_manager` and their typed interfaces; updated the
Gazebo launch, Backend task contract, integration tests, CI and documentation.

## Verification

Backend tests cover the unified lifecycle. ROS unit tests cover registry
selection and retry bounds. The Gazebo launch test exercises create acknowledgement
through assignment, pickup, delivery and completion with two isolated AMRs.

## CI / Build Impact

ROS CI now builds and tests seven packages. No dependency outside the existing
ROS 2 Jazzy and Gazebo Harmonic environment was added.

## Follow-up

Bridge task updates and multi-robot state into the Backend's unified realtime
contract, then add command operation IDs and persistence at the Backend boundary.
