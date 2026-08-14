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

Tạo hai file môi trường (đều đã bị Git ignore) và điền giá trị của Supabase
development project:

```bash
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.example apps/frontend/.env.local
```

- Backend cần `DATABASE_URL` và `SUPABASE_URL`; issuer/JWKS được suy ra từ URL.
- Frontend chỉ nhận `NEXT_PUBLIC_SUPABASE_URL` và publishable/anon key công khai.
- Không đưa database password hoặc `SUPABASE_SERVICE_ROLE_KEY` vào frontend.

```bash
# Terminal 1 — từ root repository
uv sync --all-packages --dev
make backend
```

```bash
# Terminal 2 — frontend
cd apps/frontend
npm ci
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
read -rsp "Designer access token: " DESIGNER_ACCESS_TOKEN && export DESIGNER_ACCESS_TOKEN
read -rsp "Monitor access token: " MONITOR_ACCESS_TOKEN && export MONITOR_ACCESS_TOKEN
uv run python scripts/demo_mvp.py
unset DESIGNER_ACCESS_TOKEN MONITOR_ACCESS_TOKEN
```

Hai token ngắn hạn lấy từ hai phiên Supabase demo tương ứng và không được commit
vào file `.env`. Script kiểm tra: health → baseline → chặn Monitor chạy scenario →
Designer chạy scenario → chặn Designer apply → chặn apply trước approve → Monitor
approve/apply → factory reset đúng số robot.

### 5. Chạy kiểm thử

```bash
make test
```
