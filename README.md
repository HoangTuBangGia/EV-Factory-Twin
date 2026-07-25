# Super Extraordinary X

Dự án **P-078** của nhóm **Super Extraordinary X** thuộc chương trình **VinUni AI20K Build Phase — Cohort 3**.

## Thành viên

- Nguyễn Huy Hưng
- Nguyễn Xuân Huy
- Nguyễn Tiến Đạt
- Nguyễn Thị Khánh Ly

## Khởi tạo dự án với uv

### 1. Cài đặt uv

Làm theo hướng dẫn cài đặt tại [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/).

Kiểm tra phiên bản sau khi cài:

```bash
uv --version
```

### 2. Clone repository

```bash
git clone https://github.com/AI20K-Build-Phase-Cohort-3/P-078.git
cd P-078
git switch develop
```

### 3. Cài đặt dependencies

```bash
uv sync --extra dev
```

Lệnh này tạo môi trường ảo `.venv` và cài đặt các dependency của dự án, bao gồm dependency phục vụ phát triển.

### 4. Thiết lập biến môi trường

```bash
cp .env.example .env
```

Mở `.env` và điền các API key cần thiết, đặc biệt là `AI_LOG_API_KEY`.

### 5. Chạy ứng dụng

```bash
uv run uvicorn src.main:app --reload --port 8000
```

Sau khi server khởi động:

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>

### 6. Chạy kiểm thử

```bash
make test
```
