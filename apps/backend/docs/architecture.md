# Kiến trúc — code nằm ở đâu, chạy như thế nào

Đọc file này xong bạn sẽ biết: mở file nào khi cần sửa gì, và điều gì xảy ra
mỗi 1/10 giây.

## Quy tắc phân tầng

Code chia 3 tầng. **Quy tắc quan trọng nhất: tầng trên gọi tầng dưới, không bao
giờ ngược lại.**

```
API Layer      (api/)       nhận HTTP request, trả HTTP response
    ↓
Service Layer  (services/)  toàn bộ logic nghiệp vụ nằm ở đây
    ↓
State Layer    (services/factory_state.py)   dữ liệu đang sống trong RAM
```

**Vì sao phải tách?** Nếu nhét logic vào route handler, thì logic đó chỉ chạy
được khi có người gọi HTTP. Mà mock engine chạy nền 10 lần/giây thì không gọi
HTTP — nó gọi thẳng service. Tách ra để cả hai dùng chung một logic duy nhất,
không phải viết hai lần.

Trong thực tế, một route handler trông như thế này — **chỉ 3 dòng, không có
logic gì cả**:

```python
@router.get("/{robot_id}", response_model=Robot)
async def get_robot(robot_id: str, factory_state: FactoryStateDep) -> Robot:
    robot = factory_state.get_robot(robot_id)
    if robot is None:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    return robot
```

## Bản đồ thư mục

```
apps/backend/src/ev_twin_api/
├── main.py              ← điểm khởi động: tạo app, bật engine, gắn router
│
├── api/                 ← TẦNG API: chỉ nhận request & trả response
│   ├── health.py        GET /health
│   ├── factory.py       GET /api/v1/factory
│   ├── robots.py        GET /api/v1/robots, /robots/{id}
│   ├── tasks.py         GET /api/v1/tasks, /tasks/{id}
│   ├── metrics.py       GET /api/v1/metrics
│   ├── alerts.py        GET /api/v1/alerts
│   ├── mock.py          POST /api/v1/mock/start|stop|reset|config
│   └── websocket.py     WS  /ws/factory
│
├── schemas/             ← ĐỊNH NGHĨA DỮ LIỆU (Pydantic) — hợp đồng với FE
│   ├── base.py          kiểu datetime dùng chung (ISO 8601, UTC, hậu tố Z)
│   ├── robot.py         RobotStatus, Pose, Velocity, Robot
│   ├── telemetry.py     RobotTelemetry  ← hợp đồng QUAN TRỌNG NHẤT
│   ├── task.py          TaskStatus, Task
│   ├── factory.py       Station, FactoryLayout, MockFactoryConfig
│   ├── metrics.py       FactoryMetrics
│   ├── alert.py         AlertSeverity, AlertCode, FactoryAlert
│   ├── websocket.py     envelope {type, data} + hàm dựng từng loại event
│   ├── health.py        HealthResponse
│   └── mock.py          MockControlResponse
│
├── services/            ← TẦNG SERVICE: toàn bộ logic nghiệp vụ
│   ├── factory_state.py    giữ state (robot/task/alert/metrics) — DUY NHẤT
│   ├── mock_factory.py     vòng lặp 10 Hz, điều phối mọi service khác
│   ├── movement.py         tính robot đi được tới đâu sau dt giây
│   ├── task_service.py     tạo đơn, chọn robot, chuyển trạng thái đơn
│   ├── battery_service.py  hao pin / sạc pin
│   ├── metrics_service.py  tính năng suất, thời gian chu kỳ...
│   ├── alert_service.py    sinh cảnh báo + chống spam trùng lặp
│   └── websocket_manager.py  giữ danh sách client, phát tin cho tất cả
│
└── core/                ← HẰNG SỐ & CẤU HÌNH (không có logic)
    ├── config.py        đọc biến môi trường (.env)
    ├── layout.py        20×15 m, 6 trạm, vị trí robot lúc khởi tạo
    ├── routes.py        các tuyến đường waypoint
    └── logging_config.py
```

**Cần sửa gì thì mở file nào:**

| Muốn thay đổi | Mở file |
|---|---|
| Robot đi đường nào | `core/routes.py` |
| Vị trí/số lượng trạm | `core/layout.py` |
| Tốc độ hao pin, mức sạc đầy | `services/battery_service.py` |
| Cách chọn robot cho đơn hàng | `services/task_service.py` (`select_assignment`) |
| Điều kiện phát cảnh báo | `services/alert_service.py` |
| Công thức tính năng suất | `services/metrics_service.py` |
| Thêm field vào dữ liệu gửi FE | `schemas/` — **cẩn thận, xem cảnh báo cuối trang** |

## Chuyện gì xảy ra khi bật backend

```python
# main.py — rút gọn
@asynccontextmanager
async def lifespan(app: FastAPI):
    ...
    factory_state = FactoryState(config=mock_config)  # tạo 5 robot, 6 trạm
    mock_factory = MockFactory(...)  # tạo engine
    await mock_factory.start()  # bật vòng lặp 10 Hz
    yield  # ← app phục vụ request ở đây
    await mock_factory.stop()  # tắt sạch khi shutdown
```

Điểm đáng chú ý: **mọi thứ khởi tạo bên trong `lifespan`, không phải lúc import
module.** Nghĩa là chỉ cần `import ev_twin_api.main` thì không có vòng lặp nào
chạy nền cả. Nhờ vậy test import app mà không vô tình bật engine, và khi tắt
server thì `stop()` chắc chắn được gọi.

## Vòng lặp 10 Hz — trái tim của hệ thống

Đây là phần quan trọng nhất cần hiểu. Toàn bộ mô phỏng chỉ là **một vòng lặp
lặp đi lặp lại 10 lần mỗi giây**, mỗi lần gọi là một **tick**.

```python
# services/mock_factory.py — rút gọn
async def run(self):
    while self.running:
        started = time.monotonic()
        await self.tick(0.1 * self.config.simulation_speed)
        elapsed = time.monotonic() - started
        await asyncio.sleep(max(0.0, 0.1 - elapsed))  # ngủ cho đủ 1/10 giây
```

### `simulation_speed` KHÔNG làm vòng lặp chạy nhanh hơn

Đây là chỗ rất dễ hiểu nhầm, đọc kỹ chỗ này:

- Vòng lặp **luôn** chạy đúng 10 lần/giây theo đồng hồ thật. Không đổi.
- `simulation_speed` chỉ nhân vào **`dt`** — tức "khoảng thời gian mà thế giới
  mô phỏng coi như đã trôi qua" trong tick đó.

Ví dụ với `simulation_speed = 8`: mỗi 1/10 giây thật, thế giới mô phỏng trôi
qua 0.8 giây. Robot đi xa gấp 8 lần, pin hao nhanh gấp 8 lần, nhưng frontend
vẫn nhận đúng 10 gói tin/giây — không bị ngập tin.

Vì vậy `throughput_per_hour` trong metrics tính theo **giờ mô phỏng**, không
phải giờ thật.

### Một tick làm gì — theo đúng thứ tự

```
1. Với TỪNG robot:
   a. cập nhật last_seen_at
   b. cộng/trừ pin theo trạng thái hiện tại
   c. xử lý theo trạng thái:
      · đang di chuyển  → đi tiếp; tới nơi thì chuyển trạng thái
      · PICKING         → xong, chuyển sang DELIVERING (gắn pin vào robot)
      · DROPPING        → xong, đơn COMPLETED, robot về IDLE (nhả pin)
      · CHARGING        → đủ 80% thì về IDLE
      · IDLE            → pin yếu thì đi sạc
   d. phát robot.telemetry cho mọi client WebSocket

2. Gán đơn: lặp tới khi hết cặp (robot rảnh + đơn đang chờ) khớp được

3. Sinh đơn mới nếu đã đủ task_interval_seconds

4. Tính lại toàn bộ metrics

5. Phát metrics.updated (chỉ ~1 lần/giây, không phải mỗi tick)

6. Kiểm tra & phát cảnh báo mới (nếu có)
```

### Lỗi trong tick không làm chết engine

```python
try:
    await self.tick(...)
except Exception:
    logger.exception("mock factory tick failed")  # ghi log rồi chạy tiếp
```

Nếu một tick ném lỗi, engine ghi log kèm traceback rồi **vẫn chạy tick tiếp
theo** — một lỗi nhất thời không làm sập cả mô phỏng. Nhưng nếu lỗi **10 lần
liên tiếp**, engine tự dừng và ghi log mức CRITICAL, thay vì spam lỗi vô hạn.

## Ai giữ dữ liệu?

**Chỉ `FactoryState` được phép giữ dữ liệu thay đổi được.** Không có biến global
rải rác khắp nơi. Mọi thay đổi đều đi qua nó.

Một chi tiết dễ bỏ sót nhưng quan trọng: **mọi hàm đọc đều trả về bản sao**, chứ
không trả về chính đối tượng bên trong.

```python
def get_robot(self, robot_id: str) -> Robot | None:
    robot = self.robots.get(robot_id)
    return robot.model_copy(deep=True) if robot is not None else None
```

Nhờ vậy, code bên ngoài có sửa vật thể nhận được cũng không vô tình làm hỏng
state gốc. Muốn thay đổi thật thì phải gọi `update_robot(...)` một cách rõ ràng.

Khi ID không tồn tại, hàm trả `None` — **không trả về object rỗng**. Tầng API
bắt `None` này và đổi thành lỗi HTTP 404.

## Realtime hoạt động thế nào

`WebSocketManager` giữ một `set` các client đang kết nối. Mỗi lần có gì đáng
báo, engine gọi `broadcast(...)` và tin được gửi tới **tất cả** client.

Điểm cần biết: **một client chết không làm hỏng cả buổi phát.**

```python
for connection in list(self._connections):
    try:
        await connection.send_json(payload)
    except Exception:
        dead.append(connection)  # bỏ riêng client này ra, những client
        # còn lại vẫn nhận tin bình thường
```

Mọi tin nhắn đều bọc trong một "phong bì" giống nhau, để FE chỉ cần đọc `type`
là biết cách xử lý `data`:

```json
{ "type": "robot.telemetry", "data": { ... } }
```

| `type` | Khi nào phát |
|---|---|
| `robot.telemetry` | mỗi tick, mỗi robot một gói (~10 Hz) |
| `task.updated` | mỗi khi đơn hàng đổi trạng thái |
| `metrics.updated` | ~1 lần / giây thật, không phụ thuộc `simulation_speed` |
| `alert.created` | khi có cảnh báo mới |
| `factory.reset` | khi ai đó gọi `POST /api/v1/mock/reset` |

## ⚠️ Cảnh báo trước khi sửa `schemas/`

`RobotTelemetry` là **hợp đồng quan trọng nhất giữa backend và frontend**. Đổi
tên field ở đây sẽ làm hỏng frontend ngay lập tức, và sẽ hỏng lại lần nữa khi
sau này chuyển sang ROS2.

Trước khi đổi bất cứ thứ gì trong `schemas/`, hãy báo cho team frontend và cập
nhật [`docs/api.md`](../../../docs/api.md) cùng lúc.
