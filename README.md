# EV Factory Digital Twin

Nền tảng Digital Twin mô phỏng và giám sát hoạt động vận chuyển battery pack bằng đội robot tự hành (AMR) trong khu vực Final Assembly của nhà máy xe điện.

Dự án **P-078** được phát triển bởi nhóm **Super Extraordinary X** trong chương trình **VinUni AI20K Build Phase — Cohort 3 & 4**.

## Tổng quan

Hệ thống hiện cung cấp:

- dashboard theo dõi đội AMR, task, KPI và cảnh báo;
- bản đồ nhà máy và telemetry realtime;
- REST API và WebSocket với mock factory engine tích hợp sẵn;
- mô phỏng sự kiện rời rạc cho các kịch bản vận hành;
- công cụ chạy batch và xếp hạng kịch bản theo throughput, cycle time và waiting time;
- các domain model và phép đo dùng chung trong `twin-core`.

> Trạng thái hiện tại: backend đang dùng mock factory engine. Kiến trúc giữ ổn định contract REST/WebSocket để có thể thay nguồn dữ liệu bằng ROS 2 trong giai đoạn tiếp theo.

## Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Zustand, ECharts, Tailwind CSS |
| Backend | Python 3.12, FastAPI, Pydantic, WebSocket |
| Simulation | SimPy, NumPy, pandas |
| Tooling | uv, npm, Ruff, mypy, pytest, Vitest |

## Cấu trúc repository

```text
.
├── apps/
│   ├── backend/              # FastAPI, REST API, WebSocket và mock factory
│   └── frontend/             # Dashboard Next.js
├── packages/twin-core/       # Domain model, routing và KPI dùng chung
├── services/simulation/      # Discrete-event simulation và scenario runner
├── evaluation/               # Benchmark và báo cáo so sánh scenario
├── docs/                     # Architecture, API, development và deployment
├── infra/                    # Hạ tầng triển khai (đang hoàn thiện)
├── tests/integration/        # Integration tests
├── Makefile
└── pyproject.toml            # Python workspace
```

## Yêu cầu

- Python `3.12`
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js `22`
- npm

ROS 2 Jazzy và Gazebo Harmonic chỉ cần cho phần tích hợp robot/mô phỏng vật lý trong tương lai, không bắt buộc để chạy dashboard và mock backend hiện tại.

## Bắt đầu nhanh

### 1. Clone và cài dependency

```bash
git clone https://github.com/AI20K-Build-Phase-Cohort-3/P-078.git
cd P-078

uv sync --locked --all-packages --dev
cd apps/frontend && npm ci && cd ../..
```

### 2. Chọn chế độ chạy

#### Chỉ chạy frontend với dữ liệu mock

Đây là cách nhanh nhất để xem giao diện, không cần khởi động backend:

```bash
cd apps/frontend
cp .env.example .env.local
npm run dev
```

Giữ `NEXT_PUBLIC_DATA_SOURCE=mock` trong `.env.local`, sau đó mở <http://localhost:3000>.

#### Chạy full-stack với backend realtime

Tại terminal thứ nhất, từ thư mục gốc repository:

```bash
cp apps/backend/.env.example .env
make backend
```

Backend tự khởi động mock factory engine và phục vụ tại:

- Frontend: <http://localhost:3000>
- Swagger UI: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>
- WebSocket: `ws://localhost:8000/ws/factory`

Tại terminal thứ hai:

```bash
cd apps/frontend
cp .env.example .env.local
```

Đổi giá trị sau trong `apps/frontend/.env.local`:

```dotenv
NEXT_PUBLIC_DATA_SOURCE=api
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/factory
```

Sau đó chạy:

```bash
npm run dev
```

Mở <http://localhost:3000>. Frontend sẽ lấy snapshot ban đầu qua REST API và nhận telemetry mới qua WebSocket.

## Cấu hình môi trường

Backend đọc file `.env` tại thư mục đang chạy lệnh. Các biến chính:

| Biến | Mặc định | Ý nghĩa |
|---|---:|---|
| `APP_ENV` | `development` | Môi trường chạy ứng dụng |
| `CORS_ORIGINS` | `http://localhost:3000` | Danh sách origin, phân tách bằng dấu phẩy |
| `MOCK_FACTORY_ENABLED` | `true` | Bật mock factory engine khi backend khởi động |
| `MOCK_ROBOT_COUNT` | `5` | Số AMR được mô phỏng |
| `MOCK_TASK_INTERVAL_SECONDS` | `8` | Khoảng thời gian sinh task |
| `MOCK_ROBOT_SPEED_MPS` | `1.2` | Tốc độ robot (m/s) |
| `MOCK_SIMULATION_SPEED` | `1` | Hệ số tốc độ mô phỏng |

Frontend dùng các biến `NEXT_PUBLIC_*` trong `apps/frontend/.env.local`. Xem mẫu đầy đủ tại `apps/frontend/.env.example`.

## API chính

Mọi REST endpoint nghiệp vụ nằm dưới `/api/v1`, ngoại trừ `/health`.

| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/health` | Trạng thái backend |
| `GET` | `/api/v1/factory` | Layout nhà máy |
| `GET` | `/api/v1/robots` | Danh sách AMR |
| `GET` | `/api/v1/tasks` | Danh sách task |
| `GET` | `/api/v1/metrics` | KPI vận hành |
| `GET` | `/api/v1/alerts` | Danh sách cảnh báo |
| `POST` | `/api/v1/mock/start` | Chạy mock engine |
| `POST` | `/api/v1/mock/stop` | Dừng mock engine |
| `POST` | `/api/v1/mock/reset` | Reset trạng thái mô phỏng |
| `POST` | `/api/v1/mock/config` | Cập nhật tham số mô phỏng |
| `WS` | `/ws/factory` | Stream sự kiện realtime |

Schema và contract chi tiết nằm trong [docs/api.md](docs/api.md).

## Chạy simulation và benchmark

Chạy một scenario:

```bash
uv run --package ev-factory-simulation \
  python -m ev_sim.runner \
  --scenario services/simulation/scenarios/baseline.json
```

Chạy toàn bộ scenario và tạo dataset JSON/CSV:

```bash
uv run --package ev-factory-simulation python -m ev_sim.batch
```

Xếp hạng kết quả và tạo báo cáo:

```bash
uv run --package ev-twin-evaluation python -m ev_evaluation.benchmark
```

Kết quả mặc định được ghi vào `evaluation/datasets/` và `evaluation/reports/`.

## Kiểm tra chất lượng

### Python workspace

```bash
make check
```

Hoặc chạy từng bước:

```bash
make lint
make format-check
make typecheck
make test
make test-cov
```

### Frontend

```bash
cd apps/frontend
npm run lint
npm test -- --run
npm run build
```

## Tài liệu

- [Kiến trúc hệ thống](docs/architecture.md)
- [API contract](docs/api.md)
- [Môi trường phát triển](docs/development.md)
- [Yêu cầu hệ thống](docs/requirements.md)
- [Đánh giá và benchmark](docs/evaluation.md)
- [Quy trình đóng góp](CONTRIBUTING.md)

## Thành viên

- Nguyễn Huy Hưng
- Nguyễn Xuân Huy
- Nguyễn Tiến Đạt
- Nguyễn Thị Khánh Ly
