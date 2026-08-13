# Super Extraordinary X

Dự án **P-078** của nhóm **Super Extraordinary X** thuộc chương trình **VinUni AI20K Build Phase — Cohort 3 & 4**.

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

### 3. Chạy MVP local

```bash
# Terminal 1 — từ root repository
uv sync --all-packages --dev
make backend
```

```bash
# Terminal 2 — frontend
cd apps/frontend
npm ci
cp .env.example .env.local
npm run dev
```

Sau khi hai server khởi động:

- Frontend: <http://localhost:3000>
- Swagger UI: <http://localhost:8000/docs>

Frontend mẫu dùng `NEXT_PUBLIC_DATA_SOURCE=api`, nên robot và scenario lấy dữ liệu
thật từ backend thay vì fixture.

### 4. Kiểm tra luồng MVP

Khi backend đang chạy, thực hiện:

```bash
uv run python scripts/demo_mvp.py
```

Script kiểm tra: health → baseline → run scenario → chặn apply trước approve →
approve → apply → factory reset đúng số robot.

### 5. Chạy kiểm thử

```bash
make test
```
