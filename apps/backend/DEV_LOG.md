# Backend Dev Log

> **Đây là nhật ký theo thứ tự thời gian, ghi lại quá trình làm và các lỗi đã
> gặp — không phải tài liệu để hiểu hệ thống.**
>
> Nếu bạn muốn hiểu backend làm gì và hoạt động ra sao, đọc [`docs/`](docs/)
> thay vì file này. Bắt đầu từ [`docs/README.md`](docs/README.md).
>
> Nhật ký bên dưới dừng ở BE-001. Các phần sau (BE-002 → BE-012: contracts,
> FactoryState, di chuyển, task engine, WebSocket, pin/sạc, metrics, alerts,
> mock control, integration test) được mô tả trong [`docs/`](docs/), và chi
> tiết từng bước nằm trong lịch sử commit (`git log`).

---

## 2026-08-11 — BE-001: Backend package structure & khởi động qua uv

**Đã làm:**
- Dọn scaffold cũ không khớp spec: xoá `routers/` (rỗng, chỉ còn `__pycache__`,
  không có trong git), gỡ `sqlalchemy`/`asyncpg`/`twin-core` khỏi
  `apps/backend/pyproject.toml` (không dùng ở phase mock-data).
- Thêm dependency qua `uv add --package ev-twin-api ...` (không dùng pip):
  - deps: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `websockets`
  - dev-deps: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`
- Dựng skeleton đúng yêu cầu:
  - `src/ev_twin_api/api/__init__.py` + `api/health.py` (route `/health`)
  - `src/ev_twin_api/schemas/__init__.py` (rỗng, chờ task sau)
  - `src/ev_twin_api/services/__init__.py` (rỗng, chờ task sau)
  - `src/ev_twin_api/core/__init__.py` + `core/config.py`
  - `tests/api/`, `tests/services/`, `tests/integration/` (2 dir sau đang rỗng, có `.gitkeep`)
- KHÔNG tạo file rỗng cho `robots.py`, `tasks.py`, `factory.py`, `mock.py`, `websocket.py`
  — để dành cho task sau theo đúng yêu cầu.
- `main.py`: chỉ khởi tạo `FastAPI()` + `include_router(health_router)`, không có business logic.

**Verify:** `pytest` pass, `uv run --package ev-twin-api uvicorn ev_twin_api.main:app` chạy
được và `/health` trả `{"status": "ok"}`, `ruff check` + `mypy` sạch.

**Note:** `BACKEND_IMPLEMENTATION_GUIDE.1.md` không có trong repo tại thời điểm làm task này
— đã hỏi user và được xác nhận dùng spec trong task làm contract, không tự suy diễn.

---

## 2026-08-11 — `core/config.py`: đọc config từ env

**Đã làm:**
- Dùng `pydantic-settings` (`BaseSettings`) đọc 7 biến env với default:
  `APP_ENV=development`, `CORS_ORIGINS=http://localhost:3000`,
  `MOCK_FACTORY_ENABLED=true`, `MOCK_ROBOT_COUNT=5`,
  `MOCK_TASK_INTERVAL_SECONDS=8`, `MOCK_ROBOT_SPEED_MPS=1.2`, `MOCK_SIMULATION_SPEED=1`.
- `CORS_ORIGINS`: pydantic-settings mặc định cố `json.loads` giá trị env cho field kiểu
  `list`, nên chuỗi phân tách bằng dấu phẩy thường (`"a,b"`) sẽ lỗi parse. Xử lý bằng
  `Annotated[list[str], NoDecode]` (tắt auto-decode) + `field_validator(mode="before")`
  tự `split(",")`.
- Expose settings dùng chung qua `get_settings()` có `@lru_cache` — gọi nhiều lần cùng
  1 instance.
- Bỏ `app_name`/`version`/`debug` khỏi `Settings` (không nằm trong contract 7 biến trên,
  vốn là mình tự đoán ở bước trước vì chưa có guide). `main.py` cập nhật lại: title/version
  cố định, `debug` suy ra từ `settings.app_env == "development"`.
- Tạo `apps/backend/.env.example` với đủ 7 biến. Không cần sửa `.gitignore` cho `.env` vì
  root đã có sẵn `.env` / `.env.*` + ngoại lệ `!.env.example`.

**Verify:** default đúng khi không set env, parse nhiều origin phân tách dấu phẩy đúng,
cache trả cùng instance, `pytest`/`ruff`/`mypy` đều sạch.

---

## 2026-08-11 — `main.py`: app factory, lifespan, CORS, routers

**Đã làm:**
- Viết lại `main.py` đúng 4 việc theo yêu cầu, không business logic:
  1. Tạo `FastAPI(title=..., version=..., description=...)`.
  2. `lifespan` bằng `asynccontextmanager`, hiện chỉ log `"backend started"` trước
     `yield` và `"backend stopped"` sau `yield` — chỗ mock engine sẽ gắn vào ở BE-005.
  3. `CORSMiddleware` cấu hình từ `settings.cors_origins` (không hardcode).
  4. `include_router(health_router)`.
- Không có side-effect nào chạy lúc import module — chỉ tạo `app` object; mọi thứ
  chạy nền phải qua `lifespan` (được ASGI server gọi lúc startup/shutdown, không phải
  lúc `import`).

**Vấn đề gặp phải:** `logger.info(...)` mặc định KHÔNG in ra gì vì root logger có level
`WARNING` (30) và không có handler nào được cấu hình — `logging.lastResort` cũng chỉ in
từ `WARNING` trở lên nên INFO bị nuốt hoàn toàn dù code không lỗi. Xử lý bằng
`logging.basicConfig(level=logging.INFO)` ở đầu `main.py`.

**Verify:**
- `python -c "import ev_twin_api.main"` chạy xong ngay, không có gì start ở background
  (đúng yêu cầu "không start background loop bằng side-effect lúc import").
- Chạy `uv run --package ev-twin-api uvicorn ev_twin_api.main:app` → log in đúng
  `INFO:ev_twin_api:backend started` lúc startup và `backend stopped` lúc shutdown (Ctrl+C).
- CORS: set `CORS_ORIGINS=http://localhost:3000,http://localhost:5173`, preflight
  `OPTIONS /health` với `Origin: http://localhost:5173` → header
  `access-control-allow-origin` đúng; với origin lạ (`http://evil.example`) → 400,
  không có header allow-origin.
- `pytest`/`ruff`/`mypy` đều sạch.

---

## 2026-08-11 — `api/health.py`: response_model tối thiểu

**Đã làm:**
- `GET /health` giữ nguyên KHÔNG có prefix `/api/v1` — ngoại lệ duy nhất, mọi endpoint
  khác từ giờ sẽ dùng `/api/v1`.
- Thêm `HealthResponse(BaseModel)` với `status: str`, `version: str`, khai báo
  `response_model=HealthResponse` để `/docs` (OpenAPI schema) sinh đúng schema thay vì
  `dict[str, str]` chung chung.
- Thêm `__version__ = "0.1.0"` vào `ev_twin_api/__init__.py` làm nguồn duy nhất cho app
  version — dùng chung ở cả `main.py` (`FastAPI(version=...)`) và `api/health.py`
  (response), tránh 2 nơi hardcode dễ lệch nhau.
- Model đặt inline trong `api/health.py` (không tạo `schemas/health.py`) vì scope task này
  chỉ ở mức tối thiểu để app chạy — BE-002 sẽ hoàn thiện phần schemas/health đầy đủ hơn.
- Cập nhật `tests/api/test_health.py` để assert cả `status` và `version`.

**Verify:** `pytest`/`ruff`/`mypy` sạch; kiểm tra `openapi.json` — path là `/health` (không
phải `/api/v1/health`), response schema trỏ đúng `#/components/schemas/HealthResponse` với
2 field `status`/`version`.

---

## 2026-08-11 — Logging cơ bản level INFO

**Đã làm:**
- Tách cấu hình logging ra `core/logging_config.py` (thay vì gọi `logging.basicConfig`
  trực tiếp trong `main.py`) — `configure_logging(level=logging.INFO)` dùng
  `logging.basicConfig` với format `"%(asctime)s %(levelname)s %(name)s: %(message)s"`.
  Đặt tên file `logging_config.py` chứ không phải `logging.py` để tránh gây nhầm lẫn khi
  đọc code (dù `import logging` tuyệt đối vẫn resolve đúng module chuẩn thư viện).
- `main.py` gọi `configure_logging()` 1 lần lúc import (chỉ set handler/level, không phải
  background loop nên không vi phạm rule "không side-effect chạy nền lúc import").
- Log sự kiện lifecycle `"backend started"` / `"backend stopped"` ở mức INFO (đã có từ
  task `main.py` trước, giờ format log rõ ràng hơn nhờ formatter).
- Ghi chú convention ngay trong `logging_config.py`: INFO chỉ dành cho lifecycle/thay đổi
  trạng thái quan trọng — dữ liệu tần suất cao (telemetry mỗi tick, mỗi frame WebSocket ở
  BE-005 sau này) phải dùng DEBUG trở xuống, không được log ở INFO.

**Verify:** chạy `uvicorn` → log có timestamp/level/logger name, in đúng
`... INFO ev_twin_api: backend started` lúc startup và `backend stopped` lúc shutdown.
`pytest`/`ruff`/`mypy` sạch.

---

## 2026-08-11 — Quality gates

**Đã làm:**
- Kiểm tra lại thì `Makefile` (`make check` = lint + format-check + typecheck + test) và
  `.github/workflows/ci.yml` (chạy `make check` trên push/PR vào `main`/`develop`) đã có
  sẵn từ trước (commit chore/setup của team) và khớp đúng yêu cầu 4 gate — không cần sửa.
- Phần còn thiếu: mypy chưa strict cho backend. Thêm vào root `pyproject.toml`:
  ```
  [tool.mypy]
  python_version = "3.12"
  warn_unused_configs = true

  [[tool.mypy.overrides]]
  module = "ev_twin_api.*"
  strict = true
  ```
  Chỉ strict cho `ev_twin_api.*` (module của `apps/backend`), không ép `twin_core` (package
  khác, ngoài scope task này) phải strict theo.
- Xác nhận bằng thực nghiệm: `strict = true` được phép đặt trong
  `[[tool.mypy.overrides]]` ở mypy 2.3.0 (một số version cũ mypy cấm việc này, cần set từng
  flag lẻ) — test bằng cách thêm 1 hàm không có type hint vào `core/config.py`, mypy báo
  đúng lỗi `no-untyped-def` với config strict, không báo gì nếu bỏ config. Đã dọn hàm test
  này khỏi `config.py` sau khi xác nhận.
- Type hints: strict mypy (bao gồm `disallow_untyped_defs`, `disallow_incomplete_defs`)
  pass 0 lỗi trên toàn bộ `apps/backend/src` → toàn bộ function trong package đã có type
  hint đầy đủ, không cần sửa code thêm.
- `ruff`/`ruff format` đã cấu hình sẵn ở root `pyproject.toml`, áp dụng cho cả repo
  (kể cả `apps/backend`) vì `apps/backend/pyproject.toml` không có `[tool.ruff]` riêng nên
  ruff tự tìm lên config gốc.

**Verify:** `make check` chạy sạch cả 4 gate (ruff check, ruff format --check, mypy, pytest)
trên toàn repo, bao gồm `apps/backend`.

---

## 2026-08-11 — Test `/health` + rà Definition of Done

**Đã làm:**
- Viết lại `tests/api/test_health.py`: dùng `httpx.AsyncClient` + `ASGITransport` (không
  cần server thật) thay vì so dict cứng. Validate response bằng chính
  `HealthResponse.model_validate(...)` (model thật của route trong `api/health.py`) thay vì
  hardcode lại field ngoài `status`/`version` trong test — test giờ gắn với schema thật,
  không tự bịa field.
- `ruff check` bắt lỗi thứ tự import (`pytest` phải đứng tách nhóm với `httpx` theo alpha
  trong cùng block third-party) — fix bằng `ruff check --fix`.

**Phát hiện đáng chú ý về `uv sync` trong workspace:** chạy `uv sync` (không cờ) từ ROOT
repo chỉ sync đúng project gốc (`ev-factory-digital-twin`, deps rỗng) — **gỡ mất**
fastapi/uvicorn/httpx/pydantic-settings khỏi venv chung vì các gói này thuộc `ev-twin-api`,
không phải root. Chạy `uv sync` từ TRONG `apps/backend/` thì đúng — CWD quyết định project
nào là "current project" khi không có `--package`/`--all-packages`. Dev backend nên luôn
`cd apps/backend` trước khi chạy `uv sync`/`uv run` cho riêng phần backend; dùng
`uv sync --all-packages` ở root khi cần đủ cả workspace (vd. chạy `make check`).

**Kết quả rà Definition of Done (chạy `uv sync` + `uv run uvicorn` từ trong `apps/backend/`):**
- [x] `uv sync` chạy thành công (exit 0)
- [x] `uv run uvicorn ev_twin_api.main:app --reload --port 8000` khởi động không lỗi,
      log lifecycle `backend started` xuất hiện đúng
- [x] `GET http://localhost:8000/health` → 200, `{"status":"ok","version":"0.1.0"}`
- [x] `GET http://localhost:8000/docs` → 200, Swagger UI load được (title đúng, có
      `swagger-ui` trong HTML)
- [x] Không có background loop từ import side-effect — verify bằng script đếm thread
      trước/sau `import ev_twin_api.main`: 0 thread mới, không có event loop chạy lúc import
- [x] `make check` pass đủ 4 gate (ruff check, ruff format --check, mypy, pytest) — chạy
      `uv sync --all-packages` ở root trước để venv có đủ mọi package trong workspace
- [x] `uv.lock` được cập nhật (do các thay đổi dependency từ các task trước) — CHƯA commit,
      để user tự quyết định lúc commit
- [x] Rà `git diff` không thấy pattern secret nào (api_key/secret/token/password/BEGIN);
      `.env.example` chỉ chứa placeholder, không có `.env` thật nào trong working tree

**Chưa làm (đúng theo ràng buộc):** không có Robot/Task/FactoryState/mock engine/WebSocket/
metrics/alerts nào được implement; route handler `health()` không chứa business logic;
không dùng pip install; không tự đặt tên field/contract mới ngoài `status`/`version` đã có.

---

<!-- Thêm entry mới ở trên theo format: ## YYYY-MM-DD — <task id>: <tên task> -->
