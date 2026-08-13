# FE-BE Domain Contracts

Nguồn sự thật cho các schema mà backend trả về qua REST và WebSocket. Mục tiêu:
sau này thay Mock Factory Engine bằng ROS2, các contract dưới đây không đổi, nên
frontend không phải sửa code khi backend đổi nguồn dữ liệu.

Định nghĩa Pydantic tương ứng nằm ở `apps/backend/src/ev_twin_api/schemas/`.

## Quy ước chung

- **Đơn vị:** mét (m) cho toạ độ, m/s cho vận tốc tuyến tính, rad/s cho vận tốc
  góc, rad cho `yaw`, phần trăm 0–100 cho battery.
- **Không có field pixel.** Backend luôn trả toạ độ mét; frontend tự quy đổi
  sang pixel để render.
- **Timestamp:** ISO 8601, UTC, có hậu tố `Z`, độ chính xác millisecond. Ví dụ:
  `2026-08-11T04:00:00.125Z`. Mọi field `datetime` trong response dùng chung
  format này (xem `schemas/base.py`).
- **Field nullable:** field kiểu `X | None` mà **có** giá trị mặc định `None`
  nghĩa là có thể bỏ qua khi tạo object. Field kiểu `X | None` mà **không có**
  giá trị mặc định (ví dụ `task_id`, `payload_id` trong `RobotTelemetry`) là
  **bắt buộc phải có trong payload**, nhưng giá trị của nó được phép là `null`.

## Danh sách endpoint

Mọi endpoint đều nằm dưới `/api/v1`, **trừ `/health`**.

| Method | Path | Response | Mô tả |
|---|---|---|---|
| GET | `/health` | [`HealthResponse`](#health) | Liveness, không phụ thuộc engine mock |
| GET | `/api/v1/factory` | [`FactoryLayout`](#station--factorylayout) | Kích thước nhà máy + 6 station |
| GET | `/api/v1/robots` | [`Robot[]`](#robot) | Toàn bộ AMR |
| GET | `/api/v1/robots/{robot_id}` | [`Robot`](#robot) | 1 AMR; id lạ → 404 |
| GET | `/api/v1/tasks` | [`Task[]`](#task) | Toàn bộ task |
| GET | `/api/v1/tasks/{task_id}` | [`Task`](#task) | 1 task; id lạ → 404 |
| GET | `/api/v1/metrics` | [`FactoryMetrics`](#factorymetrics) | Số liệu vận hành |
| GET | `/api/v1/alerts` | [`FactoryAlert[]`](#alertseverity--alertcode--factoryalert) | Alert đã phát |
| POST | `/api/v1/mock/start` | [`MockControlResponse`](#mockcontrolresponse) | Chạy engine mock |
| POST | `/api/v1/mock/stop` | [`MockControlResponse`](#mockcontrolresponse) | Dừng engine mock |
| POST | `/api/v1/mock/reset` | [`MockControlResponse`](#mockcontrolresponse) | Reset state về ban đầu |
| POST | `/api/v1/mock/config` | [`MockFactoryConfig`](#mockfactoryconfig) | Đổi tham số mô phỏng |
| GET | `/api/v1/scenarios` | [`Scenario[]`](#scenario-benchmark-và-phê-duyệt) | Danh sách candidate trong bộ nhớ |
| GET | `/api/v1/scenarios/baseline` | [`Scenario`](#scenario) | Benchmark baseline chuẩn của repository |
| GET | `/api/v1/scenarios/{scenario_id}` | [`Scenario`](#scenario) | Chi tiết candidate; id lạ → 404 |
| POST | `/api/v1/scenarios/run` | [`Scenario`](#scenario) | Chạy benchmark SimPy cho candidate |
| POST | `/api/v1/scenarios/{scenario_id}/approve` | [`Scenario`](#scenario) | Phê duyệt candidate đã mô phỏng |
| POST | `/api/v1/scenarios/{scenario_id}/reject` | [`Scenario`](#scenario) | Từ chối candidate đã mô phỏng |
| POST | `/api/v1/scenarios/{scenario_id}/apply` | [`Scenario`](#scenario) | Áp dụng candidate đã duyệt vào mock realtime |
| WS | `/ws/factory` | [envelope](#websocket-event-envelope) | Stream realtime |

`/ws/factory` không xuất hiện trong `/docs` (OpenAPI không mô tả WebSocket) —
hợp đồng của nó nằm ở mục [WebSocket event envelope](#websocket-event-envelope).

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
IN_PROGRESS
DELIVERED
COMPLETED
FAILED
```

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

`POST /api/v1/scenarios/run` chạy benchmark SimPy nhưng **không thay đổi** mock
factory realtime. Chỉ `POST /api/v1/scenarios/{scenario_id}/apply` mới cập nhật
mock factory và reset trạng thái vận hành hiện tại.

Scenario candidate được lưu trong bộ nhớ của process backend. Restart backend sẽ
xoá danh sách candidate và đưa bộ đếm id về đầu; đây chưa phải kho lưu trữ/audit
log bền vững. Baseline được đọc từ scenario chuẩn trong repository, có id
`baseline`, không nằm trong `GET /api/v1/scenarios` và chỉ dùng để so sánh.

### ScenarioRunRequest

Body của `POST /api/v1/scenarios/run`; tất cả field đều bắt buộc:

```json
{
  "name": "more-robots",
  "num_robots": 6,
  "num_tasks": 500,
  "task_arrival_interval": 5.0,
  "travel_time": 30.0,
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
| `travel_time` | float | `> 0` và `<= 86.400` giây | Thời gian di chuyển của một task |
| `loading_time` | float | `> 0` và `<= 86.400` giây | Thời gian load và unload |
| `simulation_time` | float | `> 0` và `<= 86.400` giây | Khoảng thời gian ảo được benchmark |

Giá trị ngoài giới hạn hoặc thiếu field → **422**.

### ScenarioStatus

```text
DRAFT
SIMULATED
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
SIMULATED ── approve ──▶ APPROVED ── apply ──▶ APPLIED
    │
    └──────── reject ──▶ REJECTED
```

- `approve` và `reject` chỉ hợp lệ khi status hiện tại là `SIMULATED`.
- `apply` chỉ hợp lệ khi status hiện tại là `APPROVED`.
- `REJECTED` và `APPLIED` là trạng thái kết thúc trong MVP.
- Chuyển trạng thái không hợp lệ → **409**; id candidate không tồn tại → **404**.

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
    "simulation_time": 3600.0
  },
  "metrics": {
    "completed_tasks": 426,
    "unfinished_tasks": 74,
    "completion_rate": 0.852,
    "throughput_per_hour": 426.0,
    "average_cycle_time": 750.0,
    "average_waiting_time": 700.0
  },
  "duration_ms": 8.4,
  "reviewed_at": null,
  "applied_at": null
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
| `reviewed_at` | datetime | có (mặc định `null`) | Được gán UTC khi approve hoặc reject |
| `applied_at` | datetime | có (mặc định `null`) | Được gán UTC khi apply thành công |

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
AlertCode (khởi điểm): LOW_BATTERY, ROBOT_WAITING, TASK_BACKLOG, STARVATION, ROBOT_ERROR
```

`GET /api/v1/alerts`. Payload của WebSocket event `alert.created`.

```json
{
  "id": "ALERT-0001",
  "severity": "WARNING",
  "code": "LOW_BATTERY",
  "message": "AMR-01 battery below threshold (18%)",
  "robot_id": "AMR-01",
  "task_id": null,
  "timestamp": "2026-08-11T04:00:00.000Z"
}
```

| Field | Type | Nullable | Ghi chú |
|---|---|---|---|
| `id` | string | không | |
| `severity` | `AlertSeverity` | không | |
| `code` | string | không | một trong `AlertCode`, hoặc code mới về sau |
| `message` | string | không | mô tả cho người xem |
| `robot_id` | string | có (mặc định `null`) | |
| `task_id` | string | có (mặc định `null`) | |
| `timestamp` | datetime | không | |

Alert có state (ví dụ `LOW_BATTERY:AMR-01`) được backend dedupe — chỉ phát khi
robot **vào** điều kiện, không lặp mỗi tick trong khi vẫn ở điều kiện đó.

## WebSocket event envelope

Mọi message trên `/ws/factory` bọc trong envelope:

```json
{
  "type": "robot.telemetry",
  "data": { }
}
```

| `type` | `data` schema | Tần suất |
|---|---|---|
| `robot.telemetry` | `RobotTelemetry` | ~10 Hz mỗi robot |
| `task.updated` | `Task` | event-driven |
| `metrics.updated` | `FactoryMetrics` | ~1 Hz theo đồng hồ thật |
| `alert.created` | `FactoryAlert` | event-driven |
| `factory.reset` | `null` | khi `POST /api/v1/mock/reset` |

## Status codes

```text
200  thành công
404  robot/task/scenario id không tồn tại
409  chuyển trạng thái scenario không hợp lệ
422  request không hợp lệ theo Pydantic
500  lỗi server không lường trước
```

Id không tồn tại trả 404, **không** trả object rỗng.
