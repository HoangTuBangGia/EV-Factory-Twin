# Development Environment

## Supported Linux Userspace

Ubuntu 24.04

## Toolchain

- Python 3.12
- uv
- Node.js 22
- ROS 2 Jazzy
- Gazebo Harmonic

## Arch Linux

ROS development runs inside an Ubuntu 24.04 Distrobox.

## Windows

ROS development runs inside WSL2 Ubuntu 24.04.

Repositories should be cloned into the WSL Linux filesystem,
not `/mnt/c`.

## Python Setup

```bash
uv sync --all-packages --dev
make check
```

## Browser E2E với Supabase hosted

Playwright chạy trình duyệt với frontend Next.js và backend FastAPI ở local,
nhưng xác thực bằng ba tài khoản thật trong một Supabase project dành riêng cho
development/E2E. Suite tạo scenario, approve/apply và thay đổi mock factory, vì
vậy không chạy nó với database production.

Chuẩn bị trước:

- `apps/frontend/.env.local` có `NEXT_PUBLIC_SUPABASE_URL` và
  `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.
- `apps/backend/.env` có `DATABASE_URL` dạng `postgresql+asyncpg://...` và
  `SUPABASE_URL` trỏ đến cùng project.
- Ba profile active có role chính xác `DESIGNER`, `MONITOR`, `ADMIN`.
- Export credential chỉ trong terminal hoặc secret store; không ghi vào file đã
  track hay thêm service-role key vào frontend.

```bash
export DESIGNER_EMAIL='designer@example.com'
export MONITOR_EMAIL='monitor@example.com'
export ADMIN_EMAIL='admin@example.com'
read -rsp 'Designer password: ' DESIGNER_PASSWORD && export DESIGNER_PASSWORD
read -rsp 'Monitor password: ' MONITOR_PASSWORD && export MONITOR_PASSWORD
read -rsp 'Admin password: ' ADMIN_PASSWORD && export ADMIN_PASSWORD
```

Cài Chromium một lần trên máy phát triển, sau đó liệt kê và chạy suite:

```bash
cd apps/frontend
npx playwright install chromium
npm run test:e2e:list
npm run test:e2e
unset DESIGNER_PASSWORD MONITOR_PASSWORD ADMIN_PASSWORD
```

Playwright tự mở `127.0.0.1:8000` và `127.0.0.1:3000`. Nếu hai server đã được
chạy thủ công ở địa chỉ khác, dùng:

```bash
E2E_EXTERNAL_SERVERS=true \
E2E_BASE_URL=http://127.0.0.1:3100 \
E2E_API_URL=http://127.0.0.1:8100 \
npm run test:e2e
```

Khi thiếu một trong sáu biến role credential, nhóm hosted RBAC được Playwright
đánh dấu `skipped` kèm danh sách tên biến còn thiếu; test direct route guard độc
lập vẫn chạy. CI chỉ cài browser và chạy hosted E2E khi đủ repository secrets:
`E2E_DATABASE_URL`, `E2E_SUPABASE_URL`, `E2E_SUPABASE_PUBLISHABLE_KEY` và sáu
biến credential ở trên. Pull request từ fork không có secrets sẽ ghi rõ lý do
skip và không cố truy cập Supabase.

Suite hosted cố ý tắt trace, screenshot và video: request đăng nhập chứa password
và response chứa token, nên các artifact đó không được lưu hoặc upload lên CI.
