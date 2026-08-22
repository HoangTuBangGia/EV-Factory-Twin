# Development Environment

## Supported Linux Userspace

Ubuntu 24.04

## Toolchain

- Python 3.12
- uv
- Node.js 22
- Docker and Supabase CLI for the local database/auth stack
- ROS 2 Jazzy
- Gazebo Harmonic

## Arch Linux

ROS development runs inside the prepared Ubuntu 24.04 Distrobox named `ros-jazzy`:

```bash
distrobox enter ros-jazzy
source /opt/ros/jazzy/setup.bash
```

## Windows

ROS development runs inside WSL2 Ubuntu 24.04.

Repositories should be cloned into the WSL Linux filesystem,
not `/mnt/c`.

## Python Setup

```bash
uv sync --all-packages --dev
make check
```

## Local Supabase

Development uses the local Supabase stack rather than a separately configured
host PostgreSQL installation. From the repository root:

```bash
make supabase-start
make supabase-status
```

Copy `apps/backend/.env.example` to the backend environment and
`apps/frontend/.env.example` to `apps/frontend/.env.local`. Replace the frontend
publishable key with the local key printed by `make supabase-status`.

Replay all migrations against the local database with:

```bash
make supabase-reset
```

`supabase-reset` deletes local Supabase data before replaying migrations. Never
run a linked reset against staging or production. Stop the local stack with:

```bash
make supabase-stop
```

## ROS multi-AMR MVP slice

Use the prepared Ubuntu 24.04 environment with ROS 2 Jazzy and Gazebo Harmonic:

```bash
source /opt/ros/jazzy/setup.bash
make ros-check
```

`make ros-deps` verifies the installed `ament_python` colcon extension directly,
then asks `rosdep` to check all remaining manifest keys. The Noble rosdep index
does not define `ament_python` as a system-package key even though it is the
standard build type used by `telemetry_bridge`.

For an edge-to-backend run, configure the backend with
`MOCK_FACTORY_ENABLED=false` and the same `EDGE_TELEMETRY_SHARED_SECRET` used by
the bridge. The acceptance run uses at least two namespaced AMRs. After
`make ros-build`, run Gazebo in one terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch amr_gazebo sim.launch.py
```

The default `amr_gazebo/config/robots.json` spawns two robots. To add robots or
change individual spawn poses, copy that file, keep every `robot_id` and namespace
unique, then run:

```bash
ros2 launch amr_gazebo sim.launch.py robots_config:=/absolute/path/robots.json
```

The launch rejects fewer than two robots, invalid namespaces, duplicate IDs and
non-finite poses before spawning any robot.

Each robot also runs the M2 navigation/state simulator. Send a typed station goal
from a sourced ROS terminal with:

```bash
ros2 action send_goal /amr_01/navigate_to_station \
  amr_interfaces/action/NavigateToStation \
  "{station_id: BATTERY_BUFFER, task_id: TASK-0001, payload_id: BP-0001, timeout_seconds: 30.0}" \
  --feedback
```

Valid default station IDs are `BATTERY_BUFFER`, `MARRIAGE_STATION` and
`CHARGING_STATION`. State is published on namespaced `battery_state`, `status`,
`task_id` and `payload_id`; `state_override` accepts `ERROR` or `OFFLINE` for
fault-path simulation. Navigation results are `SUCCESS`, `FAILED` or `TIMED_OUT`.

Create a queued battery transport task through the Task Manager service:

```bash
ros2 service call /fleet/tasks/create \
  amr_interfaces/srv/CreateTransportTask \
  "{task_id: TASK-0001, payload_id: BP-0001, pickup_station_id: BATTERY_BUFFER, dropoff_station_id: MARRIAGE_STATION, navigation_timeout_seconds: 30.0, max_retries: 1}"
```

The service response is the acceptance acknowledgement. Observe assignment and
execution results on the durable task update topic:

```bash
ros2 topic echo /fleet/task_updates amr_interfaces/msg/TaskState
```

The default launch runs one Task Manager and one Fleet Manager for all configured
robots. Task Manager owns queue/lifecycle/retry; Fleet Manager owns registry,
eligibility selection and robot navigation calls.

Run the bridge in a separate terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch telemetry_bridge telemetry_bridge.launch.py \
  backend_url:=https://YOUR_RENDER_HOST \
  robots_config:="$PWD/ros2_ws/src/amr_gazebo/config/robots.json"
```

The bridge reads its bearer secret from the `EDGE_TELEMETRY_SHARED_SECRET`
environment variable. It accepts loopback HTTP for local development only;
remote backend URLs must use HTTPS.

One bridge subscribes to every robot declared in `robots_config`, preserves a
separate latest-value delivery worker per robot, and forwards the durable
`/fleet/task_updates` stream in FIFO order. It also emits bridge-health heartbeats.
The bridge is outbound-only. Task assignment and reset commands must travel
through the edge fleet/task manager; the browser must never publish ROS messages
directly.

The Makefile disables unrelated globally installed pytest plugins and enables
`pytest-asyncio` explicitly. Tests also clear `DATABASE_URL` so a developer's
local `.env` cannot accidentally turn unit/API tests into a live PostgreSQL
dependency. Database/RLS behavior belongs in the hosted or local Supabase E2E
workflow.

## Browser E2E với Supabase staging

Playwright chạy trình duyệt với frontend Next.js và backend FastAPI ở local,
nhưng xác thực bằng hai tài khoản thật (`DESIGNER`, `MONITOR`) trong một Supabase
project staging dành riêng cho development/E2E. Suite tạo scenario, approve/apply và
kiểm tra quyền, vì vậy không chạy nó với database production.

Chuẩn bị trước:

- `apps/frontend/.env.local` có `NEXT_PUBLIC_SUPABASE_URL` và
  `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.
- `apps/backend/.env` có `DATABASE_URL` dạng `postgresql+asyncpg://...` và
  `SUPABASE_URL` trỏ đến cùng project.
- Hai profile active có role chính xác `DESIGNER` và `MONITOR`.
- Export credential chỉ trong terminal hoặc secret store; không ghi vào file đã
  track hay thêm service-role key vào frontend.

```bash
export DESIGNER_EMAIL='designer@example.com'
export MONITOR_EMAIL='monitor@example.com'
read -rsp 'Designer password: ' DESIGNER_PASSWORD && export DESIGNER_PASSWORD
read -rsp 'Monitor password: ' MONITOR_PASSWORD && export MONITOR_PASSWORD
```

Cài Chromium một lần trên máy phát triển, sau đó liệt kê và chạy suite:

```bash
cd apps/frontend
npx playwright install chromium
npm run test:e2e:list
npm run test:e2e
unset DESIGNER_PASSWORD MONITOR_PASSWORD
```

Playwright tự mở `127.0.0.1:8000` và `127.0.0.1:3000`. Nếu hai server đã được
chạy thủ công ở địa chỉ khác, dùng:

```bash
E2E_EXTERNAL_SERVERS=true \
E2E_BASE_URL=http://127.0.0.1:3100 \
E2E_API_URL=http://127.0.0.1:8100 \
npm run test:e2e
```

Khi thiếu một trong bốn biến role credential, nhóm hosted RBAC được Playwright
đánh dấu `skipped` kèm danh sách tên biến còn thiếu; test direct route guard độc
lập vẫn chạy. CI chỉ cài browser và chạy hosted E2E khi đủ repository secrets:
`E2E_DATABASE_URL`, `E2E_SUPABASE_URL`, `E2E_SUPABASE_PUBLISHABLE_KEY` và bốn
biến credential ở trên. Pull request từ fork không có secrets sẽ ghi rõ lý do
skip và không cố truy cập Supabase.

Suite hosted cố ý tắt trace, screenshot và video: request đăng nhập chứa password
và response chứa token, nên các artifact đó không được lưu hoặc upload lên CI.
