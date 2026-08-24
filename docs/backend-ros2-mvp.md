# Backend / ROS 2 MVP Contract

## Scope

This document is the checkpoint-level source of truth for the Backend/ROS 2 MVP.
The acceptance path is:

```text
2+ Gazebo AMRs → ROS 2 fleet/task runtime → telemetry bridge → FastAPI
→ WebSocket/KPI/alerts → SimPy comparison → Monitor approval
→ durable command → ROS acknowledgement/result → audit
```

ROS 2 Jazzy and Gazebo Harmonic run at the edge in Distrobox `ros-jazzy`.
Cloud Run hosts FastAPI, Vercel hosts Next.js, and Cloud SQL PostgreSQL 17
stores durable state. The browser never connects to ROS DDS.

## Roles

The product has exactly two application roles:

| Capability | DESIGNER | MONITOR |
|---|---:|---:|
| Read operational state | Yes | Yes |
| Create/version layout | Yes | No |
| Create/run/submit scenario | Yes | No |
| Approve/reject/apply scenario | No | Yes |
| Control simulation runtime | No | Yes |

User provisioning uses `make user-create`. There is no Admin role,
Admin page, or user-management API in the MVP.

## Identity and ordering

- Public robot IDs use `AMR-01`, `AMR-02`, ...; ROS namespaces use `amr_01`,
  `amr_02`, ... and Gazebo entity names equal the namespace.
- Every robot owns namespaced `cmd_vel`, `odom`, `tf`, `tf_static`, battery,
  status, task and payload state. `/clock` is the only shared simulation topic.
- A telemetry snapshot is keyed by `robot_id`. A sample older than the latest
  accepted source timestamp for that robot cannot replace live state.
- IDs for tasks, layouts, scenarios, runs, commands and operations are globally
  unique application identifiers and must not be inferred from array position.

## Lifecycle contracts

```text
Robot: IDLE | MOVING | PICKING | DELIVERING | CHARGING | ERROR | OFFLINE
Task: QUEUED → ASSIGNED → PICKUP → DELIVERING → COMPLETED
      any executable state → FAILED | TIMED_OUT → retry → QUEUED
Scenario: DRAFT → SIMULATED → SUBMITTED → APPROVED | REJECTED
          APPROVED → APPLIED
Command: PENDING → ACKNOWLEDGED → COMPLETED | FAILED | TIMED_OUT
```

Retries retain one `operation_id` and create distinct attempt records. Duplicate
delivery of a command with the same operation/attempt is idempotent. Apply is
complete only after a positive ROS execution result, not merely HTTP acceptance.

Each robot exposes the namespaced `navigate_to_station` action. Its goal carries
`station_id`, task/payload IDs and timeout; its result is exactly `SUCCESS`,
`FAILED` or `TIMED_OUT`. Navigation uses deterministic planar velocity control
for the simulation MVP, not Nav2 path planning or a collision guarantee.

Task Manager acknowledges `/fleet/tasks/create`, queues one canonical battery
transport task and publishes durable `/fleet/task_updates`. It invokes Fleet
Manager through the typed `/fleet/execute_transport_task` action. Fleet Manager
tracks namespaced robot status, battery and odometry, then selects the nearest
idle robot above the configured battery threshold. Failed and timed-out attempts
are retried only within the task's bounded retry budget.

## Runtime contracts

MOCK and ROS normalize to the same `RobotTelemetry`. Browser snapshot resources
are factory, robots, tasks, metrics and alerts. Realtime events are:

```text
robot.telemetry
task.updated
metrics.updated
alert.created
command.updated
factory.reset
```

REST owns CRUD/query/command submission. WebSocket owns realtime fan-out. The
edge bridge uses a dedicated HTTPS bearer secret and outbound connections only.

## Layout and simulation

A scenario references immutable `layout_id` and `layout_version`. Layout versions
contain stations, routes, chargers, no-go zones and congestion zones in metres.
Validation rejects non-finite geometry, out-of-bounds objects, invalid routes,
unknown station references and routes crossing no-go zones.
Layout identity metadata may be renamed or soft-archived by DESIGNER, while
every geometry/config version remains immutable and addressable by
`(layout_id, layout_version)`.

Authoritative KPI formulas live in `twin-core`: throughput, cycle time, waiting
time, fleet utilization, starvation, congestion, travel distance, delivery delay
and completion rate. SimPy models demand, robot capacity, charging, waiting and
congestion. Optimization is deterministic bounded search/heuristics over robot
count, speed, chargers, routes, layouts and demand; no ML is used.

## Persistence and alerts

Cloud SQL stores profiles/RBAC, immutable layouts, scenarios, runs/metrics,
approvals, commands/attempts/acknowledgements, alerts, audit, task history and
bounded telemetry history. Every exposed table uses RLS and required indexes.
Telemetry partition and retention follow `docs/data-retention.md`.

Alerts cover low battery, robot error, backlog, stale telemetry, bridge/ROS
disconnect, command timeout and congestion. Alert identity is a stable dedupe key;
clear closes the active occurrence and a later recurrence creates a retriggered
occurrence without losing history.

## Delivery checkpoints

1. Contract/RBAC baseline (this checkpoint).
2. Multi-AMR namespace-isolated Gazebo runtime.
3. Navigation, robot-state, fleet and task managers.
4. Multi-robot telemetry/task bridge and backend realtime path.
5. Layout/version persistence and validation.
6. SimPy/KPI/optimization.
7. Approval/apply command lifecycle.
8. Alerts, health, telemetry history and retention.
9. Render/edge deployment, CI and end-to-end acceptance.

Advanced collision physics, real robots, CAD/BIM, AI optimization and MES/ERP
integration are explicitly out of scope.
