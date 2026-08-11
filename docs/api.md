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

```json
{
  "width_m": 20,
  "height_m": 15,
  "stations": [
    { "id": "BATTERY_BUFFER", "name": "Battery Buffer", "type": "BUFFER", "x": 2, "y": 4 },
    { "id": "MARRIAGE_STATION", "name": "Marriage Station", "type": "MARRIAGE", "x": 16, "y": 8 }
  ]
}
```

| Field | Type | Nullable | Ghi chú |
|---|---|---|---|
| `width_m` / `height_m` | float | không | kích thước nhà máy, mét |
| `stations` | list of `Station` | không | |
| `Station.id` | string | không | định danh ổn định, dùng làm `pickup`/`dropoff` trong `Task` |
| `Station.name` | string | không | tên hiển thị |
| `Station.type` | string | không | loại station (giá trị cụ thể chốt ở BE-003 cùng layout) |
| `Station.x` / `Station.y` | float | không | mét |

## MockFactoryConfig

`POST /api/v1/mock/config`.

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

## FactoryMetrics

`GET /api/v1/metrics`. Payload của WebSocket event `metrics.updated` (~1 Hz).

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
| `metrics.updated` | `FactoryMetrics` | ~1 Hz |
| `alert.created` | `FactoryAlert` | event-driven |
| `factory.reset` | `null` | khi `POST /api/v1/mock/reset` |

## Status codes

```text
200  thành công
404  robot/task id không tồn tại
422  request không hợp lệ theo Pydantic
500  lỗi server không lường trước
```

Id không tồn tại trả 404, **không** trả object rỗng.
