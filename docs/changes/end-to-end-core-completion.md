# End-to-end core completion

## Outcome

This checkpoint closes the implemented browser-to-robot loop for the EV battery
intralogistics demo:

```text
Designer layout/scenario
  -> Monitor review/apply or task creation
  -> durable Backend command
  -> authenticated Telemetry Bridge
  -> typed ROS 2 Task/Fleet/Navigation contract
  -> Gazebo AMR state
  -> canonical telemetry/task updates
  -> REST/WebSocket snapshot, alerts and KPI history
  -> 2D/3D Frontend
```

Decorative plant machinery remains explicitly labelled reference geometry. The
operational source of truth is the applied layout's stations, delivery route,
no-go/congestion zones and the ROS AMR fleet.

## Frontend

- Direct protected routes preserve a safe `returnTo` during sign-in; demo
  credentials are only shown behind an explicit public development flag.
- Task creation is derived from the applied immutable layout and active delivery
  route, including a route/speed-based timeout, then follows the durable command
  lifecycle through WebSocket updates.
- The Overview 3D scene and Factory 2D plant view share layer controls for
  stations, routes, no-go and congestion geometry.
- `factory.reset` invalidates both the live snapshot and applied-layout
  projection, including resets received while snapshot recovery is in flight.
- Alert acknowledgement is server-backed and converges across clients through
  `alert.updated`; Analytics hydrates retained KPI samples and continues with
  live WebSocket samples.

## Backend and persistence

- ROS mode now owns a source-neutral 1 Hz KPI publisher; mock-only control routes
  are not mounted when mock mode is disabled.
- Transport-task commands validate against the active delivery route and carry
  navigation timeout/retry settings through the bridge to the Task Manager.
- Successful ROS scenario apply updates the Backend's active layout and emits a
  reset event so all frontend projections refetch deterministically.
- Alert acknowledgement stores the first Monitor/timestamp idempotently and is
  broadcast as an update.
- Authenticated, bounded history endpoints expose downsampled telemetry, complete
  task transitions and KPI snapshots. Migration `0018` adds task replay fields
  and durable alert acknowledgement while retaining the established retention
  jobs.
- SimPy work runs off the async request loop so scenario/optimization requests do
  not stall telemetry and WebSocket handling.

## ROS 2 and Gazebo

- Navigation loads a typed layout v3 contract, traverses the configured waypoint
  graph and rejects paths crossing no-go polygons.
- Task and Fleet Managers use per-task/per-robot reservations, allowing bounded
  multi-AMR execution without global single-task ownership.
- Low-battery robots autonomously reserve charger capacity, navigate to charging
  and remain unavailable until charging completes or fails.
- The canonical runtime is `LAYOUT-DEFAULT` v3, route `BATTERY_DELIVERY`, 120×40 m,
  1.2 m/s, two charger slots and an 8-second demand profile. Task navigation
  defaults to 120 seconds.
- Gazebo now uses the canonical footprint, boundaries and a physical obstacle for
  the configured press-clearance no-go zone.

Because `NavigateToStation.action` gained `route_id`, rebuild the ROS interfaces
and all dependent packages before launching this revision.

## Runtime topology rule

Robot speed is live-updatable. Layout/version, route, robot registry, charger
capacity and demand cadence belong to the running process and require a
controlled relaunch. Both systemd services load the same non-secret
`/etc/ev-factory-twin/runtime.env`; after changing topology, restart simulation
and bridge, verify the heartbeat identity, then retry Apply. A scenario becomes
`APPLIED` only after the ROS result is `COMPLETED`.

## Verification boundary

Focused Python, TypeScript, migration, shell, JSON/XML and static ROS checks are
the proof for this checkpoint. Full ROS/colcon/launch testing remains an
environment acceptance step because this development host has no `/opt/ros`,
`rclpy` or `colcon`. Navigation is deterministic waypoint-following Twist
control, not production Nav2; dynamic obstacle avoidance and fleet traffic
reservation are outside this checkpoint.
