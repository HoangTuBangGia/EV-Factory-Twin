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

Mở http://localhost:8000/docs — đây là trang tài liệu API tự sinh, bấm được
"Try it out" để gọi thử từng endpoint ngay trên trình duyệt.

Thử vài lệnh:

```bash
curl localhost:8000/health                  # app còn sống không
curl localhost:8000/api/v1/robots           # 5 con robot đang ở đâu
curl localhost:8000/api/v1/tasks            # các đơn chở pin
curl localhost:8000/api/v1/metrics          # năng suất, tỉ lệ robot bận...
```

Xem dòng dữ liệu realtime (cần `websockets`, đã có sẵn trong môi trường):

```bash
uv run --package ev-twin-api python3 -c "
import asyncio, json, websockets
async def main():
    async with websockets.connect('ws://127.0.0.1:8000/ws/factory') as ws:
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
  -H 'Content-Type: application/json' \
  -d '{"simulation_speed": 8, "task_interval_seconds": 2, "robot_speed_mps": 3}'
```

## Đọc tiếp gì?

| Bạn muốn biết | Đọc file |
|---|---|
| Code tổ chức ra sao, luồng chạy thế nào | [architecture.md](architecture.md) |
| Xưởng hoạt động theo quy tắc gì (robot, pin, đơn hàng, cảnh báo) | [simulation.md](simulation.md) |
| Chạy test, kiểm chứng ra sao | [testing.md](testing.md) |
| **Định dạng dữ liệu chính xác để tích hợp FE** | [`docs/api.md`](../../../docs/api.md) ở gốc repo |
| Nhật ký từng bước làm, gồm cả các lỗi đã gặp | [DEV_LOG.md](../DEV_LOG.md) |

> Nếu bạn là **frontend dev**: file bạn cần là [`docs/api.md`](../../../docs/api.md).
> Nó mô tả từng field, đơn vị, field nào được phép `null`, định dạng thời gian.

## Vài điều cần biết trước khi động vào

- **Toạ độ luôn là mét, không bao giờ là pixel.** Xưởng rộng 20 m × 15 m.
  Frontend tự quy đổi mét sang pixel để vẽ. Backend không biết gì về màn hình.
- **Dữ liệu chỉ nằm trong RAM.** Tắt backend là mất sạch, khởi động lại thì
  xưởng về trạng thái ban đầu. Đây là lựa chọn có chủ ý cho giai đoạn này;
  database sẽ thêm sau.
- **Các con số về pin là số minh hoạ cho demo**, không phải mô hình pin thật.
  Chúng được cố ý làm nhanh lên để xem được kết quả trong vài chục giây.
