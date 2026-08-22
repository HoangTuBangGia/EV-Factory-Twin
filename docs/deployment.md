# CORE Deployment Strategy

Kiến trúc production:

```text
Browser
  ├── HTTPS/WSS ──> Render: FastAPI REST + WebSocket
  └── HTTPS ──────> Vercel: Next.js frontend
```

Factory edge chạy Gazebo Harmonic, ROS 2 Jazzy, deterministic navigation
simulator, fleet/task managers và telemetry bridge. Edge chỉ mở kết nối outbound
TLS tới Render; browser không truy cập DDS. Supabase cung cấp Auth và PostgreSQL
cho backend.

Không deploy Gazebo/ROS2 lên Vercel hoặc Render. Hai nền tảng này không cung cấp
ROS DDS, Gazebo process, network discovery ổn định hoặc GPU/robotics runtime.

## Current readiness

Repository có production `apps/backend/Dockerfile`, Render Blueprint và container
CI health smoke. Vercel dùng native Next.js build với Root Directory
`apps/frontend`, nên không cần `vercel.json`. Đây là deployable configuration,
không phải bằng chứng hosted acceptance; lần chạy thật phải được ghi theo
`docs/runbooks/mvp-edge-acceptance.md`.

Không commit `.env`, `.env.local` hoặc secret. Các file này đã được `.gitignore`.

## 1. Chuẩn bị

1. Push code lên GitHub, ưu tiên merge vào `main` sau khi CI xanh.
2. Tạo tài khoản Vercel và Render, rồi kết nối cả hai với GitHub.
3. Bảo đảm CI đã xanh và checkpoint backend container đã cung cấp:
   - `render.yaml` hoặc cấu hình Render tương đương đã được kiểm thử;
   - `apps/backend/Dockerfile` nếu chọn Docker deploy;
   - `apps/frontend/package-lock.json`.

## 2. Chạy ROS2/Gazebo tại edge

Chọn một trong các phương án sau:

| Phương án | Khi dùng | Ghi chú |
|---|---|---|
| Máy Ubuntu 24.04 của team | Demo và development | Dễ debug, cần giữ máy online |
| GCP Compute Engine Ubuntu 24.04 | Demo online ổn định | Chạy headless theo `docs/runbooks/gcp-edge.md` |
| Docker Compose trên edge host | Deployment lặp lại | Dùng image ROS 2 Jazzy/Gazebo Harmonic, không dùng Vercel/Render |

Edge cần chạy các process:

```text
Gazebo world + AMR models
ROS 2 fleet/task manager
telemetry_bridge
```

Edge kết nối tới Render bằng HTTPS/WSS hoặc HTTPS telemetry ingress. Chỉ mở
outbound traffic; không mở cổng DDS cho Internet. Nếu cần điều khiển từ backend,
backend gửi command tới một edge gateway đã xác thực, gateway publish ROS2 topic
hoặc gọi ROS2 service trong mạng nội bộ.

Tối thiểu phải kiểm tra:

```bash
make ros-check
make ros-build
ros2 launch amr_gazebo sim.launch.py
ros2 launch telemetry_bridge telemetry_bridge.launch.py \
  robots_config:="$PWD/ros2_ws/src/amr_gazebo/config/robots.json"
```

`EDGE_TELEMETRY_SHARED_SECRET` chỉ nằm ở Render và edge secret store. Không đặt
secret trong frontend, Supabase client hoặc Git.

## 3. Deploy backend lên Render

1. MVP/demo dùng Render **Free Web Service**, một instance và một Uvicorn worker
   trong giai đoạn live state/WebSocket còn process-local. Chuyển sang paid khi
   cần telemetry liên tục hoặc không chấp nhận cold start.
2. Dùng **New > Blueprint** và chọn `render.yaml` trong repository.
3. Cấu hình các biến môi trường backend trên Render:

   ```env
   APP_ENV=production
    CORS_ORIGINS=https://YOUR_VERCEL_DOMAIN
    DATABASE_URL=postgresql+asyncpg://...
   DATABASE_SSL_MODE=require
   SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
    EDGE_TELEMETRY_SHARED_SECRET=GENERATE_AT_LEAST_32_RANDOM_CHARACTERS
    EDGE_TELEMETRY_MAX_FUTURE_SKEW_SECONDS=5
   ```

   `SUPABASE_JWT_ISSUER` và `SUPABASE_JWKS_URL` được suy ra từ `SUPABASE_URL`.
   Backend MVP không dùng service-role key; team tạo account trong Supabase Dashboard. Sau khi
   có URL Vercel production, phải thay `CORS_ORIGINS` bằng URL Vercel thật.
   Edge secret phải được cấu hình cùng giá trị ở Render và secret store của bridge;
   không đưa vào Vercel hoặc Supabase client config. Future-skew mặc định 5 giây
   cho phép sai lệch clock nhỏ; giá trị hợp lệ là 0–300 giây.
4. Trước deploy ứng dụng, link Supabase CLI tới đúng hosted project và chạy
   `supabase db push` như một thao tác migration riêng có kiểm soát. Không đặt
   migration trong application startup hoặc Render start command. Xem trước diff,
   backup và yêu cầu người vận hành duyệt trước khi chạy lên hosted database.
5. Chọn **Apply** và chờ service healthy.
6. Ghi lại URL backend, ví dụ:

   ```text
   https://ev-factory-twin-api.onrender.com
   ```

7. Kiểm tra backend:

   ```bash
   curl https://ev-factory-twin-api.onrender.com/health
   curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
     https://ev-factory-twin-api.onrender.com/api/v1/auth/me
   ```

Render dùng `/health` làm health check. Container lắng nghe biến `PORT` mà Render
cấp và hỗ trợ REST lẫn WebSocket trên cùng service.

## 4. Deploy frontend lên Vercel

1. Mở Vercel Dashboard, chọn **Add New > Project**.
2. Import cùng GitHub repository.
3. Trong cấu hình project chọn:

   | Cấu hình | Giá trị |
   |---|---|
   | Framework Preset | Next.js |
   | Root Directory | `apps/frontend` |
   | Install Command | `npm ci` |
   | Build Command | `npm run build` |
   | Output Directory | để mặc định |

4. Thêm năm biến môi trường cho **Production** và **Preview**:

   ```env
   NEXT_PUBLIC_DATA_SOURCE=api
   NEXT_PUBLIC_API_URL=https://ev-factory-twin-api.onrender.com
   NEXT_PUBLIC_WS_URL=wss://ev-factory-twin-api.onrender.com/ws/factory
   NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
   NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLIC_KEY
   ```

   Thay hostname ví dụ bằng hostname Render thực tế. Production bắt buộc dùng
   `https://` cho REST và `wss://` cho WebSocket để tránh mixed-content.
5. Chọn **Deploy**.
6. Ghi lại URL production ổn định, ví dụ:

   ```text
   https://ev-factory-twin.vercel.app
   ```

`NEXT_PUBLIC_*` được nhúng vào bundle tại lúc build. Sau khi sửa các biến này,
phải **Redeploy** frontend; restart đơn thuần không thay đổi bundle cũ.

## 5. Hoàn tất CORS trên Render

Trong Render Dashboard mở service backend:

1. Vào **Environment**.
2. Đổi `CORS_ORIGINS` thành origin production của Vercel, không có dấu `/` cuối:

   ```text
   https://ev-factory-twin.vercel.app
   ```

3. Nếu có nhiều frontend origin, phân tách bằng dấu phẩy:

   ```text
   https://ev-factory-twin.vercel.app,http://localhost:3000
   ```

4. Save và redeploy backend.

Backend hiện cho phép danh sách origin chính xác. URL Preview ngẫu nhiên của
Vercel sẽ không được CORS cho phép trừ khi thêm origin tương ứng trên Render.
Vì vậy production nên allowlist domain ổn định; preview chỉ chạy mock, dùng một
preview domain ổn định, hoặc được cấp origin có kiểm soát. Không dùng wildcard
CORS cho backend production.

## 6. Kiểm tra production

Mở frontend Vercel và kiểm tra:

- Mở URL khi chưa login sẽ được chuyển về `/login`.
- Designer và Monitor login vào đúng landing page/quyền tương ứng.
- Topbar chuyển từ `CONNECTING` sang `LIVE`.
- Overview hiển thị tối thiểu hai AMR đã cấu hình từ `/api/v1/robots`.
- Vị trí, pin và trạng thái robot thay đổi theo WebSocket.
- DevTools > Network có REST `200` và WebSocket `/ws/factory` trả `101`.

Có thể kiểm tra trực tiếp:

```bash
curl https://YOUR_RENDER_HOST/health
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
  https://YOUR_RENDER_HOST/api/v1/robots
```

## 7. Tự động deploy

- Vercel tự tạo Preview Deployment cho pull request và production deployment
  khi push/merge vào production branch.
- `render.yaml` dùng `autoDeployTrigger: checksPass`, vì vậy Render chỉ auto-deploy
  commit sau khi GitHub checks liên quan đã xanh. Migration production vẫn là
  thao tác riêng do con người kiểm soát.

## 8. Lưu ý vận hành

- Các endpoint `/api/v1/mock/*` yêu cầu Supabase Bearer token và role `MONITOR`.
  Backend không có chế độ bỏ qua authentication; local test dùng dependency
  override nội bộ thay vì một biến môi trường có thể vô tình lọt lên production.
- Trạng thái factory đang lưu trong RAM. Render restart hoặc redeploy sẽ reset
  robot, task, metrics và alert.
- Free instance của Render có thể ngủ khi không có traffic. Lần truy cập đầu có
  thể chậm và WebSocket sẽ ngắt khi service ngủ; frontend có reconnect tự động.
- Chỉ chạy một backend instance. Nếu scale nhiều instance khi chưa có Redis hoặc
  database dùng chung, mỗi instance sẽ có một factory state khác nhau.
- Render Free phù hợp MVP/demo nhưng có thể sleep và làm đứt WebSocket. Paid Web
  Service là yêu cầu tối thiểu khi chuyển sang telemetry vận hành liên tục.
- Chọn Supabase pooler session mode cho backend nếu Render không có IPv6 ổn định;
  không dùng transaction pooling cho kết nối SQLAlchemy lâu sống.
- Bật backup/restore phù hợp trên Supabase production và kiểm thử restore trước
  khi gọi hệ thống production-ready.
- Không đưa `DATABASE_URL`, service-role key, edge credential hoặc ROS DDS ra
  frontend. Edge chỉ mở kết nối outbound TLS tới backend.
- Rotate edge secret bằng cách cập nhật Render và bridge trong một maintenance
  window. Phiên bản hiện tại hỗ trợ một active secret, nên rotation không zero-downtime.
- Không scale ngang Render cho đến khi có durable live state và shared pub/sub.
- Không dùng `NEXT_PUBLIC_DATA_SOURCE=mock` trên Vercel nếu muốn nhận dữ liệu BE.

## 9. Rollback và xử lý lỗi

- Frontend: Vercel > Deployments > chọn bản hoạt động tốt > **Promote to Production**.
- Backend: Render > Events/Deploys > chọn commit trước và redeploy.
- CORS error: kiểm tra `CORS_ORIGINS` khớp chính xác origin Vercel.
- REST chạy nhưng WebSocket lỗi: kiểm tra URL dùng `wss://`, không phải `ws://`.
- Frontend vẫn dùng URL cũ: cập nhật biến Vercel rồi redeploy frontend.

## 10. Supabase và pg_partman

Target database là Supabase PostgreSQL 17.6.1.155. Hosted project đã xác nhận có
`pg_partman 5.3.1` và `pg_cron 1.6.4`. Migration M8 enable hai extension, tạo daily
native partitions, premake 7 ngày và retention telemetry 30 ngày. Cron gọi partman
maintenance mỗi giờ; alerts, task history và KPI snapshots được prune sau 90 ngày.
Theo dõi `cron.job_run_details` và `partman.part_config.maintenance_last_run` sau deploy.

## 11. Alternative deployment

Nếu Render không đáp ứng latency, WebSocket uptime, outbound networking hoặc
region yêu cầu, giữ Vercel/Supabase và chuyển FastAPI sang managed containers như
Fly.io, Railway, AWS App Runner hoặc ECS. Nếu cần private networking với factory,
dùng VM/container host tại edge hoặc cloud private network. Không đưa Gazebo vào
Vercel Functions. Mọi phương án vẫn giữ browser → FastAPI → edge và Supabase
Auth/RLS.
