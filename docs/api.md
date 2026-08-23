# FE-BE Domain Contracts

Nguồn sự thật cho các schema mà backend trả về qua REST và WebSocket. ROS2/Gazebo
là nguồn runtime chính của MVP; mock factory chỉ là fallback. Contract không đổi
khi chuyển giữa ROS2 và mock để frontend không phụ thuộc vào nguồn dữ liệu.

Contract nguồn-neutral nằm ở `packages/twin-core`; các schema request/response
đặc thù FastAPI nằm ở `apps/backend/src/ev_twin_api/schemas/`.

## Quy ước chung

- **Đơn vị:** mét (m) cho toạ độ, m/s cho vận tốc tuyến tính, rad/s cho vận tốc
  góc, rad cho `yaw`, phần trăm 0–100 cho battery.
- **Không có field pixel.** Backend luôn trả toạ độ mét; frontend tự quy đổi
  sang pixel để render.
- **Timestamp:** ISO 8601, UTC, có hậu tố `Z`, độ chính xác millisecond. Ví dụ:
  `2026-08-11T04:00:00.125Z`. Mọi field `datetime` trong response dùng chung
  format này (xem `twin_core.models.telemetry`). Input thiếu timezone bị từ chối.
- **Field nullable:** field kiểu `X | None` mà **có** giá trị mặc định `None`
  nghĩa là có thể bỏ qua khi tạo object. Field kiểu `X | None` mà **không có**
  giá trị mặc định (ví dụ `task_id`, `payload_id` trong `RobotTelemetry`) là
  **bắt buộc phải có trong payload**, nhưng giá trị của nó được phép là `null`.

## Danh sách endpoint

Mọi browser endpoint đều nằm dưới `/api/v1`, **trừ `/health`**. Machine edge
runtime dùng các endpoint `/internal/v1`.

Mọi browser REST endpoint ngoài `/health` yêu cầu Supabase access token trong header:

```http
Authorization: Bearer <access-token>
```

Token thiếu/sai/hết hạn trả `401`; tài khoản bị khóa hoặc sai quyền trả `403`;
dịch vụ xác thực/JWKS/profile database chưa sẵn sàng trả `503`. Role được đọc từ
`public.profiles`, không lấy từ request frontend hay generic claim
`role=authenticated` của Supabase.

Các `POST /internal/v1/*` là machine endpoint riêng cho factory-edge bridge.
Nó dùng opaque bearer secret độc lập, không dùng Supabase user token:

```http
Authorization: Bearer <EDGE_TELEMETRY_SHARED_SECRET>
```

Secret phải có ít nhất 32 ký tự, chỉ truyền qua HTTPS, không đặt trong query
string/log/frontend và không được tái sử dụng service-role key.

| Method | Path | Response | Mô tả |
|---|---|---|---|
| GET | `/health` | [`HealthResponse`](#health) | Liveness, không phụ thuộc engine mock |
| GET | `/api/v1/auth/me` | `CurrentUser` | User/profile/role đang đăng nhập |
| GET | `/api/v1/factory` | [`FactoryLayout`](#station--factorylayout) | Kích thước nhà máy + 6 station |
| GET | `/api/v1/robots` | [`Robot[]`](#robot) | Toàn bộ AMR |
| GET | `/api/v1/robots/{robot_id}` | [`Robot`](#robot) | 1 AMR; id lạ → 404 |
| GET | `/api/v1/tasks` | [`Task[]`](#task) | Toàn bộ task |
| GET | `/api/v1/tasks/{task_id}` | [`Task`](#task) | 1 task; id lạ → 404 |
| GET | `/api/v1/metrics` | [`FactoryMetrics`](#factorymetrics) | Số liệu vận hành |
| GET | `/api/v1/alerts` | [`FactoryAlert[]`](#alertseverity--alertcode--factoryalert) | Alert đã phát |
| GET | `/api/v1/layouts` | [`LayoutSummary[]`](#versioned-layout) | Layout chưa archive |
| POST | `/api/v1/layouts` | [`LayoutVersion`](#versioned-layout) | Tạo layout và version 1 |
| GET | `/api/v1/layouts/{layout_id}` | [`LayoutVersion`](#versioned-layout) | Version mới nhất |
| PATCH | `/api/v1/layouts/{layout_id}` | [`LayoutVersion`](#versioned-layout) | Đổi tên metadata |
| DELETE | `/api/v1/layouts/{layout_id}` | `204` | Soft archive layout |
| POST | `/api/v1/layouts/{layout_id}/versions` | [`LayoutVersion`](#versioned-layout) | Tạo version immutable kế tiếp |
| GET | `/api/v1/layouts/{layout_id}/versions/{version}` | [`LayoutVersion`](#versioned-layout) | Đọc version cụ thể |
| POST | `/api/v1/mock/start` | [`MockControlResponse`](#mockcontrolresponse) | Chạy engine mock local/test |
| POST | `/api/v1/mock/stop` | [`MockControlResponse`](#mockcontrolresponse) | Dừng engine mock |
| POST | `/api/v1/mock/reset` | [`MockControlResponse`](#mockcontrolresponse) | Reset state về ban đầu |
| POST | `/api/v1/mock/config` | [`MockFactoryConfig`](#mockfactoryconfig) | Đổi tham số mô phỏng |
| GET | `/api/v1/scenarios` | [`Scenario[]`](#scenario-benchmark-và-phê-duyệt) | Danh sách candidate theo thứ tự tạo |
| GET | `/api/v1/scenarios/baseline` | [`Scenario`](#scenario) | Benchmark baseline chuẩn của repository |
| GET | `/api/v1/scenarios/{scenario_id}` | [`Scenario`](#scenario) | Chi tiết candidate; id lạ → 404 |
| POST | `/api/v1/scenarios/run` | [`Scenario`](#scenario) | Chạy benchmark SimPy cho candidate |
| POST | `/api/v1/scenarios/{scenario_id}/submit` | [`Scenario`](#scenario) | DESIGNER submit candidate đã mô phỏng |
| POST | `/api/v1/optimizations/run` | `OptimizationResult` | Đánh giá và xếp hạng tối đa 64 candidate |
| POST | `/api/v1/scenarios/{scenario_id}/approve` | [`Scenario`](#scenario) | Phê duyệt candidate đã mô phỏng |
| POST | `/api/v1/scenarios/{scenario_id}/reject` | [`Scenario`](#scenario) | Từ chối candidate đã mô phỏng |
| POST | `/api/v1/scenarios/{scenario_id}/apply` | `Command` | Tạo durable apply command PENDING |
| GET | `/api/v1/commands` | `Command[]` | Danh sách command/attempt |
| GET | `/api/v1/commands/{operation_id}` | `Command` | Chi tiết command |
| POST | `/api/v1/commands/{operation_id}/retry` | `Command` | MONITOR retry failed/timeout command |
| WS | `/ws/factory` | [envelope](#websocket-event-envelope) | Stream realtime |
| POST | `/internal/v1/telemetry` | `TelemetryIngressResponse` | Edge bridge gửi một canonical robot sample |
| POST | `/internal/v1/task-updates` | `EdgeUpdateResponse` | Edge bridge gửi một ROS task transition |
| POST | `/internal/v1/bridge-health` | `EdgeUpdateResponse` | Edge bridge gửi heartbeat và delivery counters |

Ma trận quyền REST hiện tại:

| Nhóm endpoint | DESIGNER | MONITOR |
|---|---:|---:|
| GET auth/factory/robot/task/KPI/alert/scenario/layout | Có | Có |
| Create/version/rename/archive layout | Có | Không |
| `POST /scenarios/run` | Có | Không |
| Approve/Reject/Apply scenario | Không | Có |
| Start/Stop/Reset/Config MockFactory | Không | Có |

MVP chỉ có hai application role. User provisioning thực hiện bằng Supabase Dashboard.
WebSocket dùng cùng Supabase access token nhưng gửi token trong message đầu tiên,
không đặt token trên query string.

`/ws/factory` không xuất hiện trong `/docs` (OpenAPI không mô tả WebSocket) —
hợp đồng của nó nằm ở mục [WebSocket event envelope](#websocket-event-envelope).

## Versioned layout

`layouts` giữ identity và tên mutable; `layout_versions` giữ geometry/config
append-only. `DELETE` chỉ đặt `archived_at`: layout biến mất khỏi list nhưng các
version vẫn đọc được theo ID để scenario/audit có thể tham chiếu ổn định.

Factory UI xác định layout runtime bằng scenario `APPLIED` mới nhất và tải chính
xác `layout_id` + `layout_version` bất biến. Khi chưa có scenario APPLIED, UI dùng
layout mặc định đã version hóa; telemetry vẫn tiếp tục hiển thị nếu việc tải layout
thất bại tạm thời. Event `factory.reset` làm frontend tải lại projection này để
layout vừa APPLIED xuất hiện mà không cần reload trang.

```json
{
  "layout_id": "LAYOUT-0001",
  "name": "Battery transfer zone",
  "version": 1,
  "width": 20.0,
  "height": 15.0,
  "stations": [
    {"id": "BATTERY_BUFFER", "type": "BATTERY_BUFFER", "x": 2.0, "y": 4.0},
    {"id": "MARRIAGE_STATION", "type": "MARRIAGE_STATION", "x": 16.0, "y": 8.0},
    {"id": "CHARGING_STATION", "type": "CHARGING_STATION", "x": 2.0, "y": 12.0}
  ],
  "routes": [{
    "id": "BATTERY_DELIVERY",
    "start_station_id": "BATTERY_BUFFER",
    "end_station_id": "MARRIAGE_STATION",
    "waypoints": [{"x": 2.0, "y": 4.0}, {"x": 16.0, "y": 8.0}]
  }],
  "no_go_zones": [],
  "congestion_zones": [{
    "id": "CONGESTION_01",
    "delay_multiplier": 1.25,
    "points": [{"x": 10.0, "y": 6.0}, {"x": 13.0, "y": 6.0}, {"x": 13.0, "y": 9.0}]
  }],
  "config": {
    "robot_count": 2,
    "demand_interval_seconds": 8.0,
    "robot_speed_mps": 1.0,
    "charger_count": 1
  },
  "created_by": "00000000-0000-0000-0000-000000000001",
  "created_at": "2026-08-22T02:00:00Z",
  "archived_at": null
}
```

Create body là `{ "name": string, "content": <geometry/config> }`; create-version
body là `{ "content": <geometry/config> }`. `layout_id`, `version`, actor và
timestamps luôn do Backend/PostgreSQL tạo. Validation từ chối coordinate không
hữu hạn/out-of-bounds, ID trùng, thiếu station type bắt buộc, polygon suy biến/tự
cắt, route tham chiếu station lạ, endpoint không khớp station và route/station
đi vào no-go zone. Congestion zone không cấm route và dùng
`delay_multiplier` trong `[1, 10]`.

## Edge telemetry ingress

`POST /internal/v1/telemetry` nhận đúng một `RobotTelemetry` source-neutral. Chỉ
một trusted bridge được hỗ trợ trong deployment hiện tại; holder của shared secret
có thể gửi sample cho mọi robot đã đăng ký. Multi-bridge identity/allowlist là
follow-up bảo mật riêng. Mock
factory phải được dừng trước khi edge gửi dữ liệu để hai source không ghi đè nhau.

The ROS bridge sends `pose` and `velocity` from namespaced odometry, uses the
edge host UTC timestamp, and joins battery, status, task and payload state from
the same robot namespace. One process loads the fleet JSON and maintains a
separate latest-value worker per robot, so a slow robot delivery cannot overwrite
another robot's pending sample.

Response `200`:

```json
{
  "status": "ACCEPTED",
  "robot_id": "AMR-01",
  "source_timestamp": "2026-08-11T04:00:00.125Z",
  "ingested_at": "2026-08-11T04:00:00.150Z"
}
```

`status` là `ACCEPTED` hoặc `IGNORED_STALE`. Sample có timestamp bằng/cũ hơn
`last_seen_at` là idempotent no-op và không broadcast. Sample được nhận sẽ cập
nhật runtime robot state và phát cùng event `robot.telemetry` cho browser. Timestamp
mới hơn backend UTC quá `EDGE_TELEMETRY_MAX_FUTURE_SKEW_SECONDS` (mặc định 5 giây)
bị từ chối để không làm hỏng stale ordering; ngưỡng cấu hình hợp lệ là 0–300 giây.

| Condition | Status |
|---|---:|
| Missing/wrong edge credential | `401` |
| Edge secret chưa cấu hình | `503` |
| Unknown `robot_id` | `404` |
| Mock factory đang chạy | `409` |
| Invalid telemetry body | `422` |
| Timestamp vượt quá future-skew cho phép | `422` |

`POST /internal/v1/task-updates` maps the durable ROS `/fleet/task_updates`
stream to the canonical Backend `Task`, rejects equal/older timestamps per
`task_id`, updates REST snapshots and broadcasts `task.updated`. The bridge uses
a FIFO delivery worker so lifecycle transitions are not coalesced.

`POST /internal/v1/bridge-health` accepts `bridge_id`, `CONNECTED | DEGRADED`,
the configured robot IDs, UTC timestamp, cumulative delivery counters and the
latest per-robot delivery error. Equal/older heartbeats are ignored per
`bridge_id`. Health is currently process-local diagnostic state; durable health
and disconnect alerts belong to the alerts/persistence checkpoint.

## RobotStatus

Hợp đồng quan trọng nhất cùng với `RobotTelemetry` — dùng nhất quán ở mọi nơi
trạng thái robot xuất hiện (REST, WebSocket).

```text
IDLE
MOVING_TO_PICKUP
PICKING
DELIVERING
DROPPING
MOVING_TO_CHARGER
WAITING
CHARGING
ERROR
OFFLINE
```

## Robot

`GET /api/v1/robots`, `GET /api/v1/robots/{robot_id}` trả về (hoặc danh sách)
schema này.

```json
{
  "id": "AMR-01",
  "name": "AMR-01",
  "status": "IDLE",
  "pose": { "x": 5.0, "y": 12.0, "yaw": 0.0 },
  "velocity": { "linear": 0.0, "angular": 0.0 },
  "battery": 100.0,
  "task_id": null,
  "payload_id": null,
  "last_seen_at": "2026-08-11T04:00:00.000Z"
}
```

| Field | Type | Nullable | Ghi chú |
|---|---|---|---|
| `id` | string | không | ví dụ `AMR-01` |
| `name` | string | không | tên hiển thị |
| `status` | `RobotStatus` | không | |
| `pose` | `Pose` | không | `{x, y, yaw}` — mét, mét, rad |
| `velocity` | `Velocity` | không | `{linear, angular}` — m/s, rad/s |
| `battery` | float | không | `0 <= battery <= 100` |
| `task_id` | string | có (mặc định `null`) | task đang gán, nếu có |
| `payload_id` | string | có (mặc định `null`) | pin đang mang, nếu có |
| `last_seen_at` | datetime | không | ISO 8601 UTC |

## RobotTelemetry — hợp đồng quan trọng nhất

Payload của WebSocket event `robot.telemetry`, bắn ở tần suất ~10 Hz cho mỗi
robot đang hoạt động. Đây là ranh giới FE-BE quan trọng nhất của toàn dự án —
**không đổi tên field sau khi frontend bắt đầu tích hợp realtime.**

```json
{
  "timestamp": "2026-08-11T04:00:00.125Z",
  "robot_id": "AMR-01",
  "pose": { "x": 12.4, "y": 7.8, "yaw": 1.57 },
  "velocity": { "linear": 1.1, "angular": 0.0 },
  "battery": 82.4,
  "status": "DELIVERING",
  "task_id": "TASK-0102",
  "payload_id": "BP-0102"
}
```

| Field | Type | Nullable | Ghi chú |
|---|---|---|---|
| `timestamp` | datetime | không | thời điểm tick sinh ra sample này |
| `robot_id` | string | không | |
| `pose` | `Pose` | không | |
| `velocity` | `Velocity` | không | |
| `battery` | float | không | `0 <= battery <= 100` |
| `status` | `RobotStatus` | không | |
| `task_id` | string | **có, nhưng field bắt buộc phải có mặt** | `null` khi robot không có task |
| `payload_id` | string | **có, nhưng field bắt buộc phải có mặt** | `null` khi robot không mang pin |

## TaskStatus

```text
QUEUED
ASSIGNED
PICKUP
DELIVERING
TIMED_OUT
IN_PROGRESS
DELIVERED
COMPLETED
FAILED
```

`IN_PROGRESS` and `DELIVERED` are read-compatibility values for snapshots from
before M3. New MOCK and ROS task flows emit the canonical MVP lifecycle:
`QUEUED → ASSIGNED → PICKUP → DELIVERING → COMPLETED`, with `FAILED` and
`TIMED_OUT` as execution outcomes.

## Task

`GET /api/v1/tasks`, `GET /api/v1/tasks/{task_id}` trả về (hoặc danh sách) schema
này. Payload của WebSocket event `task.updated`.

```json
{
  "task_id": "TASK-0001",
  "type": "DELIVER_BATTERY",
  "payload_id": "BP-0001",
  "pickup": "BATTERY_BUFFER",
  "dropoff": "MARRIAGE_STATION",
  "assigned_robot_id": "AMR-02",
  "status": "IN_PROGRESS",
  "created_at": "2026-08-11T04:00:00.000Z",
  "started_at": "2026-08-11T04:00:05.000Z",
  "completed_at": null
}
```

| Field | Type | Nullable | Ghi chú |
|---|---|---|---|
| `task_id` | string | không | ví dụ `TASK-0001` |
| `type` | string | không | mặc định `"DELIVER_BATTERY"` |
| `payload_id` | string | không | ví dụ `BP-0001` |
| `pickup` | string | không | station id |
| `dropoff` | string | không | station id |
| `assigned_robot_id` | string | có (mặc định `null`) | |
| `status` | `TaskStatus` | không | |
| `created_at` | datetime | không | |
| `started_at` | datetime | có (mặc định `null`) | |
| `completed_at` | datetime | có (mặc định `null`) | |

## Station / FactoryLayout

`GET /api/v1/factory` trả về `FactoryLayout`.

Nhà máy 20 m × 15 m, luôn trả về đúng 6 station với toạ độ cố định (deterministic
— khởi động lại backend không làm đổi giá trị):

```json
{
  "width_m": 20,
  "height_m": 15,
  "stations": [
    { "id": "BATTERY_BUFFER", "name": "Battery Buffer", "type": "BUFFER", "x": 2, "y": 4 },
    { "id": "INTERSECTION_A", "name": "Intersection A", "type": "WAYPOINT", "x": 8, "y": 4 },
    { "id": "INTERSECTION_B", "name": "Intersection B", "type": "WAYPOINT", "x": 12, "y": 8 },
    { "id": "MARRIAGE_STATION", "name": "Marriage Station", "type": "MARRIAGE", "x": 16, "y": 8 },
    { "id": "CHARGING_STATION", "name": "Charging Station", "type": "CHARGER", "x": 2, "y": 12 },
    { "id": "IDLE_ZONE", "name": "Idle Zone", "type": "IDLE", "x": 5, "y": 12 }
  ]
}
```

| Field | Type | Nullable | Ghi chú |
|---|---|---|---|
| `width_m` / `height_m` | float | không | kích thước nhà máy, mét |
| `stations` | list of `Station` | không | 6 station như trên |
| `Station.id` | string | không | định danh ổn định, dùng làm `pickup`/`dropoff` trong `Task` |
| `Station.name` | string | không | tên hiển thị |
| `Station.type` | string | không | xem bảng giá trị bên dưới |
| `Station.x` / `Station.y` | float | không | mét |

`Station.type` khai báo là `string` (không phải enum) để backend thêm loại station
mới mà không phá schema. Các giá trị hiện có, FE có thể dùng để chọn icon:

| `type` | Ý nghĩa |
|---|---|
| `BUFFER` | Kho pin — điểm lấy hàng |
| `WAYPOINT` | Điểm trung chuyển trên tuyến, robot đi qua chứ không dừng làm việc |
| `MARRIAGE` | Trạm lắp pin vào xe — điểm trả hàng |
| `CHARGER` | Trạm sạc |
| `IDLE` | Khu vực chờ, nơi AMR khởi tạo |

FE nên xử lý `type` lạ bằng một icon mặc định thay vì giả định chỉ có 5 giá trị này.

## Mock control

Điều khiển engine mô phỏng. Các endpoint này chỉ phục vụ demo/điều khiển mock —
khi thay mock bằng ROS2 sau này chúng sẽ biến mất, nên **FE không nên xây tính
năng nghiệp vụ phụ thuộc vào chúng.**

### MockControlResponse

`POST /api/v1/mock/start`, `/stop`, `/reset` đều trả về schema này — trạng thái
engine **sau khi** hành động đã thực hiện xong:

```json
{
  "running": true,
  "tick_count": 128,
  "simulated_elapsed_seconds": 12.8
}
```

| Field | Type | Nullable | Ghi chú |
|---|---|---|---|
| `running` | bool | không | engine có đang chạy vòng lặp 10 Hz hay không |
| `tick_count` | int | không | số tick đã chạy; `/reset` đưa về 0 |
| `simulated_elapsed_seconds` | float | không | thời gian **mô phỏng** đã trôi (đã nhân `simulation_speed`), dùng để tính throughput; `/reset` đưa về 0 |

| Endpoint | Tác dụng |
|---|---|
| `POST /api/v1/mock/start` | Chạy engine. Idempotent — gọi nhiều lần không tạo thêm vòng lặp |
| `POST /api/v1/mock/stop` | Dừng engine. Idempotent. REST vẫn phục vụ được state hiện tại |
| `POST /api/v1/mock/reset` | Đưa toàn bộ state về ban đầu (robot, task, alert, metrics, bộ đếm) và phát event `factory.reset` |

### MockFactoryConfig

`POST /api/v1/mock/config` — body là schema dưới đây, response trả lại chính
config đã được áp dụng.

```json
{
  "robot_count": 5,
  "task_interval_seconds": 8.0,
  "robot_speed_mps": 1.2,
  "simulation_speed": 1.0,
  "low_battery_threshold": 20.0
}
```

| Field | Type | Default | Range |
|---|---|---|---|
| `robot_count` | int | 5 | 1–10 |
| `task_interval_seconds` | float | 8.0 | 1.0–60.0 |
| `robot_speed_mps` | float | 1.2 | 0.1–3.0 |
| `simulation_speed` | float | 1.0 | 0.25–10.0 |
| `low_battery_threshold` | float | 20.0 | 0–100 |

Giá trị ngoài khoảng cho phép → **422**.

**Thời điểm có hiệu lực** — điểm dễ gây hiểu nhầm:

- `task_interval_seconds`, `robot_speed_mps`, `simulation_speed`,
  `low_battery_threshold` được engine đọc lại mỗi tick → **có hiệu lực ngay ở
  tick kế tiếp.**
- `robot_count` chỉ quyết định số AMR **lúc khởi tạo**, nên `/config` không tự
  sinh thêm/bớt robot. Muốn thấy số robot mới, gọi thêm `POST /api/v1/mock/reset`.
  `/config` cố ý **không** tự reset, vì reset sẽ xoá sạch task/tiến trình đang chạy.

## Scenario benchmark và phê duyệt

Nhóm endpoint này tạo vòng MVP human-in-the-loop:

```text
chạy benchmark → xem KPI → approve/reject → apply nếu đã approve
```

`POST /api/v1/scenarios/run` chạy mô phỏng battery logistics SimPy nhưng **không thay đổi** mock
factory realtime. Chỉ `POST /api/v1/scenarios/{scenario_id}/apply` mới cập nhật
mock factory và reset trạng thái vận hành hiện tại.

Khi có `DATABASE_URL`, candidate và business audit được lưu trong PostgreSQL nên
vẫn còn sau khi backend restart. Chế độ local/test không cấu hình database mới
dùng repository in-memory và sẽ mất dữ liệu khi process dừng. Baseline được đọc
từ scenario chuẩn trong repository mã nguồn, có id `baseline`, không nằm trong
`GET /api/v1/scenarios` và chỉ dùng để so sánh. Baseline resolve
`LAYOUT-DEFAULT` version 1, route `BATTERY_DELIVERY` và chạy cùng logistics engine
cùng chín KPI authoritative như candidate; khác biệt chỉ nằm ở input scenario.

### ScenarioRunRequest

Body của `POST /api/v1/scenarios/run`. Mỗi run bắt buộc tham chiếu đúng một
`layout_id` + `layout_version` bất biến và một route thuộc version đó:

```json
{
  "name": "more-robots",
  "layout_id": "LAYOUT-DEFAULT",
  "layout_version": 1,
  "route_id": "BATTERY_DELIVERY",
  "num_robots": 6,
  "num_tasks": 500,
  "task_arrival_interval": 5.0,
  "travel_time": 1.0,
  "robot_speed_mps": 1.2,
  "charger_count": 2,
  "loading_time": 10.0,
  "simulation_time": 3600.0
}
```

| Field | Type | Giới hạn | Ý nghĩa |
|---|---|---|---|
| `name` | string | 1–80 ký tự, không được chỉ có khoảng trắng | Tên candidate |
| `num_robots` | int | 1–10 | Số robot khả dụng |
| `num_tasks` | int | 1–10.000 | Tổng task cần tạo trong benchmark |
| `task_arrival_interval` | float | 1,0–60,0 giây | Khoảng cách giữa hai task mới |
| `travel_time` | float | `> 0` và `<= 86.400` giây | Field tương thích; backend tính lại từ route/speed/congestion |
| `loading_time` | float | `> 0` và `<= 86.400` giây | Thời gian load và unload |
| `simulation_time` | float | `> 0` và `<= 86.400` giây | Khoảng thời gian ảo được benchmark |

Giá trị ngoài giới hạn hoặc thiếu field → **422**.

Backend lấy khoảng cách và congestion multiplier từ geometry của layout, rồi
mô phỏng từng robot, battery discharge/charge, charger waiting và route contention.
Kết quả trả đủ KPI authoritative: throughput, cycle time, waiting time, fleet
utilization, starvation, congestion, travel distance, delivery delay và
completion rate.

### Flow optimization

`POST /api/v1/optimizations/run` (DESIGNER) nhận các danh sách layout version,
route, số robot, speed, charger và demand interval. Backend chạy tích Descartes
tối đa 64 tổ hợp, lưu từng candidate như một scenario `SIMULATED`, rồi xếp hạng
deterministic theo completion/throughput trước, tiếp đến delay, starvation,
congestion, cycle time và chi phí cấu hình. Response gồm `recommendation`, số
candidate đã đánh giá và toàn bộ `ranking`. Search lớn hơn 64 hoặc route không
thuộc layout trả **422**.

### ScenarioStatus

```text
DRAFT
SIMULATED
SUBMITTED
APPROVED
REJECTED
APPLIED
```

MVP hiện tại tạo candidate trực tiếp ở `SIMULATED`; `DRAFT` được giữ trong
contract để mở rộng workflow sau này nhưng chưa có endpoint tạo draft.

Các chuyển trạng thái hợp lệ:

```text
POST /run
    │
    ▼
SIMULATED ── submit ──▶ SUBMITTED ── approve ──▶ APPROVED
                              │                       │
                              └──── reject ──▶ REJECTED
                                                      │ apply command COMPLETED
                                                      ▼
                                                   APPLIED
```

- `submit` chỉ creator DESIGNER thực hiện từ `SIMULATED`.
- `approve` và `reject` chỉ hợp lệ khi status hiện tại là `SUBMITTED`.
- `apply` chỉ hợp lệ khi status hiện tại là `APPROVED`.
- `REJECTED` và `APPLIED` là trạng thái kết thúc trong MVP.
- Chuyển trạng thái không hợp lệ → **409**; id candidate không tồn tại → **404**.

### Apply command

`POST /api/v1/scenarios/{id}/apply` không đổi scenario ngay. Nó trả command với
`operation_id`, status `PENDING`, timeout/retry budget và attempt 1. Edge bridge
chủ động lease command bằng shared secret, POST ACK, gọi typed ROS service rồi
POST `COMPLETED` hoặc `FAILED`. Scenario chỉ chuyển `APPROVED → APPLIED` sau
`COMPLETED`. Retry giữ nguyên `operation_id` và tạo attempt number mới; topology
không thể hot-apply phải trả `FAILED` với lý do cần relaunch Gazebo.

Backend chạy timeout sweep độc lập với browser và edge polling. Cadence mặc định
là 1 giây, cấu hình bằng `COMMAND_TIMEOUT_SWEEP_SECONDS`; attempt đã lease quá
`lease_expires_at` chuyển `TIMED_OUT`, tạo/cập nhật alert, audit và phát
`command.updated`. Frontend `/commands` hydrate lịch sử qua REST rồi hợp nhất các
update WebSocket theo `operation_id`. Cả hai role được đọc; chỉ MONITOR được retry.

### Scenario

Tất cả endpoint scenario trả về schema này (endpoint list trả về mảng):

```json
{
  "id": "SCN-0001",
  "name": "more-robots",
  "status": "SIMULATED",
  "config": {
    "num_robots": 6,
    "num_tasks": 500,
    "task_arrival_interval": 5.0,
    "travel_time": 30.0,
    "loading_time": 10.0,
    "simulation_time": 3600.0,
    "layout_id": "LAYOUT-DEFAULT",
    "layout_version": 1,
    "route_id": "BATTERY_DELIVERY",
    "robot_speed_mps": 1.2,
    "charger_count": 2,
    "route_distance_m": 19.66,
    "congestion_multiplier": 1.08
  },
  "metrics": {
    "completed_tasks": 426,
    "unfinished_tasks": 74,
    "completion_rate": 0.852,
    "throughput_per_hour": 426.0,
    "average_cycle_time": 750.0,
    "average_waiting_time": 700.0,
    "fleet_utilization_percent": 88.2,
    "starvation_events": 4,
    "congestion_percent": 12.5,
    "travel_distance": 8375.16,
    "average_delivery_delay": 42.1
  },
  "duration_ms": 8.4,
  "created_at": "2026-08-14T03:00:00.000Z",
  "created_by": "00000000-0000-0000-0000-000000000001",
  "reviewed_at": null,
  "reviewed_by": null,
  "applied_at": null,
  "applied_by": null,
  "version": 1
}
```

| Field | Type | Nullable | Ghi chú |
|---|---|---|---|
| `id` | string | không | Candidate có dạng `SCN-0001`; baseline có id `baseline` |
| `name` | string | không | Tên scenario |
| `status` | `ScenarioStatus` | không | Trạng thái workflow hiện tại |
| `config` | `ScenarioConfig` | không | Sáu tham số benchmark trong request, không gồm `name` |
| `metrics.completed_tasks` | int | không | `>= 0` |
| `metrics.unfinished_tasks` | int | không | `>= 0` |
| `metrics.completion_rate` | float | không | Từ 0 đến 1 |
| `metrics.throughput_per_hour` | float | không | Task hoàn thành mỗi giờ mô phỏng |
| `metrics.average_cycle_time` | float | không | Giây, gồm cả thời gian chờ |
| `metrics.average_waiting_time` | float | không | Giây chờ robot trung bình |
| `duration_ms` | float | không | Thời gian thực backend dùng để chạy benchmark, không phải thời gian ảo |
| `created_at` | datetime | không | Thời điểm chạy/lưu candidate |
| `created_by` | UUID | có với baseline | Người chạy candidate; baseline không có actor |
| `reviewed_at` | datetime | có (mặc định `null`) | Được gán UTC khi approve hoặc reject |
| `reviewed_by` | UUID | có (mặc định `null`) | Monitor approve hoặc reject |
| `applied_at` | datetime | có (mặc định `null`) | Được gán UTC khi apply thành công |
| `applied_by` | UUID | có (mặc định `null`) | Monitor apply |
| `version` | int | không | Optimistic-concurrency token, tăng sau mỗi transition |

### Ánh xạ khi apply

Apply giữ nguyên tốc độ robot, tốc độ simulation và ngưỡng pin hiện tại. Chỉ hai
tham số scenario được ánh xạ sang mock factory realtime:

| Scenario config | MockFactory config | Hiệu lực khi apply |
|---|---|---|
| `num_robots` | `robot_count` | Có; reset tạo lại số robot tương ứng |
| `task_arrival_interval` | `task_interval_seconds` | Có; đổi nhịp sinh task realtime |
| `num_tasks` | — | Không; chỉ dùng cho benchmark |
| `travel_time` | — | Không; chỉ dùng cho benchmark |
| `loading_time` | — | Không; chỉ dùng cho benchmark |
| `simulation_time` | — | Không; chỉ dùng cho benchmark |

Apply sẽ reset robot, task, alert, metrics và phát WebSocket event
`factory.reset`; dữ liệu vận hành đang có sẽ bị xoá.

Backend update scenario bằng điều kiện đồng thời trên `status` và `version`, nên
nếu hai Monitor gửi transition cùng lúc chỉ một request thành công; request còn
lại nhận **409**. Người tạo scenario không được review hoặc apply chính scenario
đó. Scenario transition và audit liên quan dùng chung một SQL transaction.

Trong một backend process, apply và các lệnh mock `start/stop/reset/config` dùng
chung một control lock. Vì vậy reset/config thủ công không thể chen giữa lúc một
scenario đang thay đổi và reset factory. Deploy MVP chỉ chạy **một worker/process**;
multi-instance cần một command worker hoặc distributed lock/outbox ở phase sau.

Apply còn thay đổi state mock factory trong RAM nên không thể atomic tuyệt đối
với PostgreSQL. Backend giữ row lock trong lúc reset và khôi phục cấu hình/reset
lại factory nếu reset, audit hoặc commit lỗi. Nếu chính bước khôi phục cũng lỗi,
backend ghi log kỹ thuật mức error để operator can thiệp.

## Business audit

Audit chưa có browser endpoint trong MVP hiện tại. Mỗi event durable có
`actor_id`, snapshot `actor_role`, `action`, `before_data`, `after_data`,
`request_id` và `created_at`. Bảng này append-only; chỉ Monitor active được đọc
qua Supabase RLS khi cần điều tra. Các action scenario hiện có là `SCENARIO_RUN`,
`SCENARIO_APPROVED`, `SCENARIO_REJECTED`, `SCENARIO_APPLIED`; reset thủ công và
reset do apply đều tạo `FACTORY_RESET`. Reset/config thủ công ghi event
`*_REQUESTED` trước side effect và event hoàn tất dùng cùng `request_id`; nhờ đó
nếu side effect hoặc audit hoàn tất lỗi vẫn còn durable intent để điều tra. Các
operation result sẽ bổ sung action command ở checkpoint command path.

## Health

`GET /health` — **ngoại lệ duy nhất không nằm dưới `/api/v1`.**

```json
{
  "status": "ok",
  "app_env": "development",
  "version": "0.1.0",
  "uptime_seconds": 12.48,
  "timestamp": "2026-08-11T04:00:00.125Z"
}
```

| Field | Type | Nullable | Ghi chú |
|---|---|---|---|
| `status` | string | không | luôn là `"ok"` |
| `app_env` | string | không | `development` / `production` … |
| `version` | string | không | version của package `ev-twin-api` |
| `uptime_seconds` | float | không | tính từ lúc app khởi động (monotonic clock) |
| `timestamp` | datetime | không | ISO 8601 UTC |

Health phản ánh "app còn sống", **không** phụ thuộc engine mock: vẫn trả 200 kể
cả sau khi `POST /api/v1/mock/stop`.

## FactoryMetrics

`GET /api/v1/metrics`. Payload của WebSocket event `metrics.updated` (~1 Hz theo
đồng hồ thật, không phụ thuộc `simulation_speed`).

```json
{
  "completed_tasks": 12,
  "throughput_per_hour": 60.0,
  "average_cycle_time_seconds": 50.0,
  "active_tasks": 2,
  "queued_tasks": 1,
  "starvation_events": 0,
  "fleet_utilization_percent": 40.0
}
```

Tất cả field không nullable.

## AlertSeverity / AlertCode / FactoryAlert

```text
AlertSeverity: INFO, WARNING, CRITICAL
AlertStatus: ACTIVE, CLEARED
AlertCode: LOW_BATTERY, ROBOT_WAITING, TASK_BACKLOG, STARVATION, ROBOT_ERROR,
STALE_TELEMETRY, BRIDGE_DISCONNECTED, COMMAND_TIMEOUT, CONGESTION
```

`GET /api/v1/alerts`. `alert.created` phát khi condition được kích hoạt hoặc
retrigger; `alert.updated` phát bản ghi `CLEARED` để browser loại cảnh báo ngay
mà không cần reload snapshot.

```json
{
  "id": "4e52ddcb-99cb-4bb7-a256-adac65a32cf2",
  "dedupe_key": "LOW_BATTERY:AMR-01",
  "severity": "WARNING",
  "code": "LOW_BATTERY",
  "status": "ACTIVE",
  "message": "AMR-01 battery below threshold (18%)",
  "robot_id": "AMR-01",
  "task_id": null,
  "operation_id": null,
  "timestamp": "2026-08-11T04:00:00.000Z",
  "last_seen_at": "2026-08-11T04:00:00.000Z",
  "cleared_at": null
}
```

| Field | Type | Nullable | Ghi chú |
|---|---|---|---|
| `id` | UUID | không | một occurrence; retrigger tạo UUID mới |
| `dedupe_key` | string | không | duy nhất trong các alert `ACTIVE` |
| `severity` | `AlertSeverity` | không | |
| `code` | `AlertCode` | không | |
| `status` | `AlertStatus` | không | `ACTIVE` hoặc `CLEARED` |
| `message` | string | không | mô tả cho người xem |
| `robot_id` | string | có (mặc định `null`) | |
| `task_id` | string | có (mặc định `null`) | |
| `operation_id` | UUID | có (mặc định `null`) | command liên quan nếu có |
| `timestamp` | datetime | không | |
| `last_seen_at` | datetime | không | lần cuối điều kiện còn được quan sát |
| `cleared_at` | datetime | có | bắt buộc khi `CLEARED` |

Alert có state (ví dụ `LOW_BATTERY:AMR-01`) được backend dedupe — chỉ phát khi
robot **vào** điều kiện, không lặp mỗi tick trong khi vẫn ở điều kiện đó. Khi
điều kiện hết, occurrence chuyển `CLEARED`; lần xuất hiện sau tạo occurrence mới.

## WebSocket event envelope

Browser chỉ được kết nối từ một `Origin` có trong `CORS_ORIGINS`. Sau khi server
accept WebSocket, client phải gửi JSON dưới đây trong thời gian cấu hình (mặc
định 5 giây):

```json
{
  "type": "auth",
  "access_token": "<supabase-access-token>"
}
```

Socket chưa được thêm vào broadcast pool ở bước này, nên không thể nhận
telemetry trước khi xác thực. Khi token và profile active hợp lệ, server trả:

```json
{
  "type": "auth.ok",
  "data": {
    "user_id": "00000000-0000-0000-0000-000000000001",
    "display_name": "Factory Monitor",
    "role": "MONITOR",
    "expires_at": 1786676400
  }
}
```

`expires_at` là Unix epoch seconds. Client chỉ chuyển sang `LIVE` sau
`auth.ok`; backend tự đóng và loại socket khỏi pool khi JWT hết hạn. Close code:

| Code | Ý nghĩa |
|---:|---|
| `1008` | Origin không được phép |
| `1013` | JWKS/profile database tạm thời không khả dụng |
| `4401` | Auth message/token thiếu, sai, hết hạn hoặc gửi quá thời gian |
| `4403` | Profile không tồn tại hoặc user bị khóa |

Sau `auth.ok`, mọi message server trên `/ws/factory` bọc trong envelope:

```json
{
  "type": "robot.telemetry",
  "data": { }
}
```

| `type` | `data` schema | Tần suất |
|---|---|---|
| `auth.ok` | user id, display name, role, expiry | một lần sau auth |
| `robot.telemetry` | `RobotTelemetry` | ~10 Hz mỗi robot |
| `task.updated` | `Task` | event-driven |
| `metrics.updated` | `FactoryMetrics` | ~1 Hz theo đồng hồ thật |
| `alert.created` | `FactoryAlert` | event-driven |
| `alert.updated` | `FactoryAlert` | khi lifecycle chuyển sang `CLEARED` |
| `command.updated` | `Command` | khi command/attempt đổi trạng thái |
| `factory.reset` | `null` | khi `POST /api/v1/mock/reset` |

## Status codes

```text
200  thành công
401  access token REST thiếu, sai hoặc hết hạn
403  user inactive hoặc không đủ role
404  robot/task/scenario id không tồn tại
409  chuyển trạng thái scenario không hợp lệ
422  request không hợp lệ theo Pydantic
503  dịch vụ xác thực tạm thời không khả dụng
500  lỗi server không lường trước
```

Id không tồn tại trả 404, **không** trả object rỗng.
