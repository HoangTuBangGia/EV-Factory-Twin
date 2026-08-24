# MVP Edge Acceptance Runbook

> Superseded for deployment/auth configuration by ADR-0005 and
> `docs/deployment.md`. Provider-specific Render/Vercel/Supabase steps below are
> retained only as the record of the earlier acceptance design and must not be run.

## Purpose

Prove the production-shaped path from two Gazebo AMRs at the factory edge to
Render, Vercel and Supabase. Run this only after Backend, Database, Frontend,
Container and ROS CI are green.

## Preconditions

- The edge is either Distrobox `ros-jazzy` for local development or the GCP VM
  prepared with `docs/runbooks/gcp-edge.md`.
- Render runs the single Free MVP/demo Web Service from `render.yaml`; warm its
  health endpoint before timed acceptance measurements.
- Vercel deploys `apps/frontend` with the production environment documented in
  `docs/deployment.md`.
- Hosted Supabase migrations are current and the DESIGNER/MONITOR accounts exist.
- Render and the edge use the same `EDGE_TELEMETRY_SHARED_SECRET` (at least 32
  characters). Never paste it into shell history, logs, screenshots or frontend
  environment variables.

## 1. Verify cloud services

From the host, replace the placeholders and keep access tokens out of committed
files:

```bash
curl --fail --silent --show-error https://YOUR_RENDER_HOST/health
curl --fail --silent --show-error \
  -H "Authorization: Bearer ${MONITOR_ACCESS_TOKEN}" \
  https://YOUR_RENDER_HOST/api/v1/factory
```

Confirm the health response reports `app_env=production`. A production process
must refuse startup when PostgreSQL, Supabase, the edge secret, explicit CORS or
`MOCK_FACTORY_ENABLED=false` is missing.

## 2. Build and launch the edge

Set the repository root, enter Distrobox only for local development, and build
the exact committed workspace:

```bash
distrobox enter ros-jazzy
export EV_TWIN_ROOT=/path/to/EV-Factory-Twin
cd "$EV_TWIN_ROOT"
source /opt/ros/jazzy/setup.bash
make ros-check
source ros2_ws/install/setup.bash
ros2 launch amr_gazebo sim.launch.py
```

On GCP, verify the already-installed systemd units instead of launching duplicate
processes:

```bash
systemctl status ev-twin-simulation.service ev-twin-bridge.service
```

The default config must create `AMR-01`/`amr_01` and `AMR-02`/`amr_02`. In a
second sourced terminal, verify isolation before sending work:

```bash
ros2 topic list | rg '^/amr_0[12]/(cmd_vel|odom|tf|battery_state|status|task_id|payload_id)$'
ros2 node list | rg 'amr_01|amr_02|fleet_manager|task_manager'
```

## 3. Connect the bridge

Export the edge secret through the operator's secret mechanism, then launch:

```bash
ros2 launch telemetry_bridge telemetry_bridge.launch.py \
  backend_url:=https://YOUR_RENDER_HOST \
  robots_config:="$PWD/ros2_ws/src/amr_gazebo/config/robots.json"
```

In Vercel, login as MONITOR. Both robot IDs must appear independently and the
WebSocket must become LIVE. In Render logs, confirm bridge health without secret
or bearer-token output.

## 4. Execute battery logistics

In another sourced edge terminal:

```bash
ros2 topic echo /fleet/task_updates amr_interfaces/msg/TaskState
ros2 service call /fleet/tasks/create \
  amr_interfaces/srv/CreateTransportTask \
  "{task_id: TASK-ACCEPT-0001, payload_id: BP-ACCEPT-0001, pickup_station_id: BATTERY_BUFFER, dropoff_station_id: MARRIAGE_STATION, navigation_timeout_seconds: 30.0, max_retries: 1}"
```

Record evidence of `QUEUED → ASSIGNED → PICKUP → DELIVERING → COMPLETED`, the
selected robot moving in Gazebo, its battery decreasing, and both robots keeping
separate telemetry. Then send that robot to `CHARGING_STATION` and confirm its
battery increases while CHARGING.

## 5. Simulate, optimize and apply

As DESIGNER in Vercel:

1. Create an immutable layout version with stations/routes/charger and a
   congestion zone.
2. Create and run a baseline scenario.
3. Run bounded optimization and verify no more than 64 deterministic candidates.
4. Compare all nine authoritative KPI and submit the chosen scenario.

As MONITOR:

1. Approve and apply the scenario.
2. Observe `PENDING → ACKNOWLEDGED → COMPLETED` in `command.updated`.
3. Confirm the scenario becomes APPLIED only after the Fleet Manager result.
4. Confirm the APPLIED congestion polygon changes runtime congestion evaluation.

Repeat once with the edge stopped. The command must become TIMED_OUT and create a
deduplicated command-timeout/bridge-disconnect alert. Restart the edge, explicitly
retry the same `operation_id`, and confirm a new attempt completes.

## 6. Persistence and audit evidence

After a Backend restart, verify Supabase still contains the layout/version,
scenario/run/KPI, approval, command attempts/acknowledgements, alerts, task
history, audit records and retained telemetry. Confirm telemetry rows for both
robot IDs exist in separate daily partitions and inspect recent pg_cron/partman
maintenance results as described in `docs/data-retention.md`.

## 7. Record the acceptance result

Capture commit SHA, Render/Vercel deployment IDs, Supabase migration version,
edge config checksum, timestamps, pass/fail for each section, ROS-to-Backend
latency, Backend-to-browser latency and browser FPS. Do not record credentials.

This is an operational acceptance run, not a CI replacement. CI independently
checks Backend/DB, frontend, ROS and the production container; this run proves
the networked boundary using the actual hosted services.
