# Test & kiểm tra chất lượng

## Chạy nhanh

```bash
make check      # chạy cả 4 cổng kiểm tra — luôn chạy lệnh này trước khi mở PR
```

`make check` gồm 4 bước, hỏng bước nào là dừng luôn ở đó:

| Bước | Lệnh | Kiểm tra điều gì |
|---|---|---|
| 1. Lint | `ruff check .` | Lỗi cú pháp, import thừa, code smell |
| 2. Format | `ruff format --check .` | Code đã format đúng chuẩn chưa |
| 3. Type | `mypy ...` | Kiểu dữ liệu (chế độ **strict** cho backend) |
| 4. Test | `pytest` | 141 test |

Kết quả mong đợi (các con số sẽ tăng dần khi dự án thêm file, miễn là không có
dòng nào báo lỗi):

```
All checks passed!
91 files already formatted
Success: no issues found in 46 source files
141 passed in 8.84s
```

> Bước Format cũng kiểm cả **code block Python nằm trong file `.md`**, nên sửa
> tài liệu cũng có thể làm hỏng gate này. Chạy `make format` là tự sửa xong.

Chạy riêng từng phần:

```bash
make lint
make format          # tự động sửa format (khác với format-check chỉ kiểm tra)
make typecheck
make test
uv run pytest apps/backend/tests/services/test_movement.py -v   # 1 file
uv run pytest -k "battery" -v                                   # lọc theo tên
```

## Test nằm ở đâu

```
apps/backend/tests/
├── conftest.py       fixture `client` dùng chung (app thật + WebSocket)
├── schemas/          kiểm tra hợp đồng dữ liệu: validate, serialize
├── services/         kiểm tra logic nghiệp vụ  ← phần đông nhất
├── api/              kiểm tra endpoint HTTP & WebSocket
└── integration/      kiểm tra toàn luồng từ đầu tới cuối
```

## 141 test đó kiểm những gì

| Nhóm | File | Kiểm tra |
|---|---|---|
| Di chuyển | `services/test_movement.py` | Toạ độ đổi, `yaw` đổi, đúng thứ tự waypoint, không ra khỏi biên, chạy 2 lần ra kết quả y hệt |
| Trạng thái robot | `services/test_task_service.py` | Từng bước `IDLE → ... → IDLE`, gắn/nhả pin đúng lúc |
| Pin & sạc | `services/test_battery_service.py` | Hao khi chạy, tăng khi sạc, không âm, không quá 100 |
| Sinh đơn | `services/test_task_service.py` | Đúng chu kỳ, ID tuần tự không trùng |
| Gán đơn | `services/test_task_service.py` | Chọn robot gần nhất, loại robot pin yếu |
| Hoàn thành đơn | `services/test_mock_factory.py` | Đơn đi hết vòng đời, robot về `IDLE` |
| Metrics | `services/test_metrics_service.py` | Công thức đúng, không chia cho 0 |
| Starvation | `services/test_metrics_service.py` | Một đơn chỉ bị đếm 1 lần |
| Chống spam alert | `services/test_alert_service.py` | Vào tình trạng → 1 alert; giữ nguyên → im; thoát rồi vào lại → alert mới |
| REST API | `api/test_*.py` | 200/404/422 đúng, dữ liệu trả về đúng schema |
| WebSocket | `api/test_websocket.py` | Kết nối, nhận telemetry, nhiều client, ngắt kết nối không sập |
| Toàn luồng | `integration/test_end_to_end.py` | Xem mục dưới |

## Test toàn luồng (integration)

Đây là test đáng chú ý nhất. Nó dựng **app thật**, mở **WebSocket thật**, rồi
theo dõi đúng kịch bản:

```
engine chạy → sinh đơn → gán robot → robot di chuyển
   → telemetry được phát → giao hàng xong → metrics thay đổi
```

Sau đó nó **đối chiếu chéo** kết quả quan sát qua WebSocket với dữ liệu lấy từ
`GET /api/v1/tasks` và `GET /api/v1/metrics` — cả ba đường (engine, REST,
WebSocket) phải khớp nhau thì test mới đạt.

## Nguyên tắc viết test trong dự án này

**1. Kiểm tra hành vi nghiệp vụ, không chỉ kiểm mã HTTP.**
Test `GET /api/v1/robots` trả 200 gần như vô nghĩa. Phải kiểm nó trả về đúng 5
robot, đúng ID, đúng vị trí.

**2. Không dùng số ngẫu nhiên, không phụ thuộc thời gian thật khi tránh được.**
Phần lớn test logic gọi thẳng `tick(dt)` với `dt` cố định thay vì `sleep`, nên
kết quả lặp lại y hệt mỗi lần chạy và không bị chậm.

**3. Test bất đồng bộ thì assert theo ngưỡng, không assert con số chính xác.**
Ví dụ viết `assert tick_count >= 4` chứ không phải `== 5`, vì máy CI có thể
chậm hơn máy bạn.

**4. Validate bằng chính schema thật, không tự chép lại field.**

```python
body = HealthResponse.model_validate(response.json())  # ✅ gắn với schema thật
assert body["status"] == "ok"  # ❌ tự đoán cấu trúc
```

## Nếu test hỏng

```bash
uv run pytest -x                    # dừng ngay ở test hỏng đầu tiên
uv run pytest --lf                  # chỉ chạy lại các test đã hỏng lần trước
uv run pytest -vv -k "ten_test"     # chạy 1 test, in chi tiết
uv run pytest -s                    # cho phép in log/print ra màn hình
```

**Nếu chạy test làm biến mất thư viện:** đừng chạy `uv sync` trần từ thư mục
gốc. Đây là repo dạng workspace nhiều package, `uv sync` không cờ sẽ chỉ đồng bộ
package gốc và **gỡ mất** fastapi/uvicorn. Dùng đúng lệnh này:

```bash
uv sync --all-packages --dev
```

## CI tự động

`.github/workflows/ci.yml` chạy đúng `make check` trên GitHub.

**Cần biết:** CI chỉ kích hoạt khi push hoặc mở PR vào nhánh `main` / `develop`.
Push lên nhánh feature thì **không có CI nào chạy** — muốn thấy CI xanh, phải mở
PR vào `main` hoặc `develop`.

CI cài thư viện bằng `uv sync --locked`, nghĩa là nếu `uv.lock` không khớp với
`pyproject.toml` thì CI hỏng ngay. Khi thêm thư viện, luôn commit cả hai file:

```bash
uv add --package ev-twin-api <tên-thư-viện>   # không dùng pip install
git add apps/backend/pyproject.toml uv.lock
```
