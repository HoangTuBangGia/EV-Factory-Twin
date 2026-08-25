# Backend — Tài liệu

Chào bạn. Đây là backend của **EV Factory Digital Twin**. Tài liệu này viết cho
người **chưa từng đọc code** của dự án — đọc hết trang này (~5 phút) là hiểu
backend làm gì và chạy được nó.

## Backend này làm gì?

Nói ngắn gọn: **nó giả lập một xưởng lắp ráp xe điện, rồi kể lại cho frontend
nghe mọi thứ đang xảy ra trong xưởng đó.**

Trong xưởng có 5 con robot tự hành (AMR — Autonomous Mobile Robot). Việc của
chúng là chở pin từ **kho pin** sang **trạm lắp pin vào xe**. Backend liên tục
tính toán: robot đang ở toạ độ nào, đang chở pin nào, pin của chính nó còn bao
nhiêu phần trăm, đơn hàng nào đang chờ, có sự cố gì không.

Hiện tại **không có robot thật, không có Gazebo, không có ROS2**. Toàn bộ là mô
phỏng bằng Python thuần. Nhưng dữ liệu bắn ra frontend đã được thiết kế đúng
theo định dạng mà robot thật sẽ dùng sau này — nên khi thay mô phỏng bằng ROS2,
**frontend không phải sửa một dòng nào.** Đó là mục tiêu quan trọng nhất của
toàn bộ backend này.

```
   ┌──────────────────────┐
   │  Mock Factory Engine │  ← "bộ não", chạy 10 lần mỗi giây
   │  (giả lập cái xưởng) │
   └──────────┬───────────┘
              │ cập nhật
              ▼
   ┌──────────────────────┐
   │     FactoryState     │  ← nơi giữ trạng thái: robot, task, alert, metrics
   └──────────┬───────────┘
              │ đọc ra
        ┌─────┴─────┐
        ▼           ▼
     REST       WebSocket
   (chụp ảnh)   (quay video)
        └─────┬─────┘
              ▼
          Frontend
```

**REST và WebSocket khác nhau chỗ nào?** REST là bạn *hỏi thì mới trả lời* —
hợp với việc lấy dữ liệu một lần (danh sách trạm, danh sách task). WebSocket là
backend *tự động đẩy* dữ liệu về liên tục mà không cần hỏi — hợp với việc vẽ
robot đang chạy trên màn hình theo thời gian thực.

## Chạy thử trong 2 phút

Cần: Python 3.12 và [uv](https://docs.astral.sh/uv/).

```bash
# từ thư mục gốc của repo
uv sync --all-packages --dev

uv run --package ev-twin-api \
  uvicorn ev_twin_api.main:app --app-dir apps/backend/src --reload
```

Mở http://localhost:8000/docs — đây là trang tài liệu API tự sinh. `/health` là
public; mọi endpoint nghiệp vụ cần access token do Backend phát hành. Gọi
`POST /api/v1/auth/login`, sau đó bấm **Authorize** và
nhập token của tài khoản demo để gọi thử.

Thử vài lệnh:

```bash
curl localhost:8000/health                  # app còn sống không
read -rsp "Access token: " ACCESS_TOKEN && export ACCESS_TOKEN
curl -H "Authorization: Bearer $ACCESS_TOKEN" localhost:8000/api/v1/robots
curl -H "Authorization: Bearer $ACCESS_TOKEN" localhost:8000/api/v1/tasks
curl -H "Authorization: Bearer $ACCESS_TOKEN" localhost:8000/api/v1/metrics
```

Xem dòng dữ liệu realtime (cần `websockets`, đã có sẵn trong môi trường):

```bash
uv run --package ev-twin-api python3 -c "
import asyncio, json, os, websockets
async def main():
    async with websockets.connect(
        'ws://127.0.0.1:8000/ws/factory',
        origin='http://localhost:3000',
    ) as ws:
        await ws.send(json.dumps({'type': 'auth', 'access_token': os.environ['ACCESS_TOKEN']}))
        print(json.loads(await ws.recv()))  # auth.ok
        for _ in range(10):
            print(json.loads(await ws.recv()))
asyncio.run(main())
"
```

Bạn sẽ thấy các gói tin chạy liên tục kiểu:

```json
{"type": "robot.telemetry", "data": {"robot_id": "AMR-01", "pose": {"x": 5.1, ...}}}
```

Nếu muốn xem robot chạy nhanh hơn cho dễ quan sát, tăng tốc mô phỏng:

```bash
curl -X POST localhost:8000/api/v1/mock/config \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"robot_count":5,"simulation_speed":8,"task_interval_seconds":2,"robot_speed_mps":3,"low_battery_threshold":20}'
```

Lệnh đổi config chỉ thành công với token role `MONITOR`. Chạy
`unset ACCESS_TOKEN` khi kiểm tra xong.

## Đọc tiếp gì?

| Bạn muốn biết | Đọc file |
|---|---|
| Code tổ chức ra sao, luồng chạy thế nào | [architecture.md](architecture.md) |
| Xưởng hoạt động theo quy tắc gì (robot, pin, đơn hàng, cảnh báo) | [simulation.md](simulation.md) |
| Chạy test, kiểm chứng ra sao | [testing.md](testing.md) |
| **Định dạng dữ liệu chính xác để tích hợp FE** | [`docs/api.md`](../../../docs/api.md) ở gốc repo |
| Vì sao một quyết định lại làm như vậy | Lịch sử commit: `git log --oneline` |

> Nếu bạn là **frontend dev**: file bạn cần là [`docs/api.md`](../../../docs/api.md).
> Nó mô tả từng field, đơn vị, field nào được phép `null`, định dạng thời gian.

## Vài điều cần biết trước khi động vào

- **Toạ độ luôn là mét, không bao giờ là pixel.** Xưởng rộng 20 m × 15 m.
  Frontend tự quy đổi mét sang pixel để vẽ. Backend không biết gì về màn hình.
- **State realtime của xưởng vẫn nằm trong RAM.** Tắt backend thì robot/task/KPI
  đang chạy trở về trạng thái ban đầu. Khi có `DATABASE_URL`, profile, scenario,
  actor review/apply và audit log được lưu bền vững trong PostgreSQL; nếu thiếu
  biến này backend chỉ dùng repository in-memory cho local/test và ghi cảnh báo.
- **Các con số về pin là số minh hoạ cho demo**, không phải mô hình pin thật.
  Chúng được cố ý làm nhanh lên để xem được kết quả trong vài chục giây.
