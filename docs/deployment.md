# Deploy frontend lên Vercel và backend lên Render

Kiến trúc production:

```text
Browser
  ├── HTTPS/WSS ──> Render: FastAPI REST + WebSocket
  └── HTTPS ──────> Vercel: Next.js frontend
```

Không commit `.env`, `.env.local` hoặc secret. Các file này đã được `.gitignore`.

## 1. Chuẩn bị

1. Push code lên GitHub, ưu tiên merge vào `main` sau khi CI xanh.
2. Tạo tài khoản Vercel và Render, rồi kết nối cả hai với GitHub.
3. Bảo đảm repository có các file sau:
   - `render.yaml`
   - `apps/backend/Dockerfile`
   - `apps/frontend/package-lock.json`

## 2. Deploy backend lên Render

1. Mở Render Dashboard, chọn **New > Blueprint**.
2. Chọn repository này. Render tự đọc `render.yaml` ở root.
3. Cấu hình các biến môi trường backend trên Render:

   ```env
   APP_ENV=production
   CORS_ORIGINS=http://localhost:3000
   DATABASE_URL=postgresql://...
   DATABASE_SSL_MODE=require
   SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVER_ONLY_KEY
   ```

   `SUPABASE_JWT_ISSUER` và `SUPABASE_JWKS_URL` được suy ra từ `SUPABASE_URL`.
   Backend không cần service-role key cho login/RBAC; chỉ endpoint Admin mời user
   cần key này. Nếu team tạo account trong Dashboard, có thể bỏ trống nó. Sau khi
   có URL Vercel production, phải thay `CORS_ORIGINS` bằng URL Vercel thật.
4. Chọn **Apply** và chờ image được build.
5. Ghi lại URL backend, ví dụ:

   ```text
   https://ev-factory-twin-api.onrender.com
   ```

6. Kiểm tra backend:

   ```bash
   curl https://ev-factory-twin-api.onrender.com/health
   curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
     https://ev-factory-twin-api.onrender.com/api/v1/auth/me
   ```

Render dùng `/health` làm health check. Container lắng nghe biến `PORT` mà Render
cấp và hỗ trợ REST lẫn WebSocket trên cùng service.

## 3. Deploy frontend lên Vercel

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

## 4. Hoàn tất CORS trên Render

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

## 5. Kiểm tra production

Mở frontend Vercel và kiểm tra:

- Mở URL khi chưa login sẽ được chuyển về `/login`.
- Designer, Monitor và Admin login vào đúng landing page/quyền tương ứng.
- Topbar chuyển từ `CONNECTING` sang `LIVE`.
- Overview hiển thị 5 AMR từ `/api/v1/robots`.
- Vị trí, pin và trạng thái robot thay đổi theo WebSocket.
- DevTools > Network có REST `200` và WebSocket `/ws/factory` trả `101`.

Có thể kiểm tra trực tiếp:

```bash
curl https://YOUR_RENDER_HOST/health
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
  https://YOUR_RENDER_HOST/api/v1/robots
```

## 6. Tự động deploy

- Vercel tự tạo Preview Deployment cho pull request và production deployment
  khi push/merge vào production branch.
- Render Blueprint đặt `autoDeployTrigger: checksPass`, nên backend chỉ tự deploy
  commit mới sau khi GitHub CI thành công.

## 7. Lưu ý vận hành

- Các endpoint `/api/v1/mock/*` yêu cầu Supabase Bearer token và role `MONITOR`.
  Backend không có chế độ bỏ qua authentication; local test dùng dependency
  override nội bộ thay vì một biến môi trường có thể vô tình lọt lên production.
- Trạng thái factory đang lưu trong RAM. Render restart hoặc redeploy sẽ reset
  robot, task, metrics và alert.
- Free instance của Render có thể ngủ khi không có traffic. Lần truy cập đầu có
  thể chậm và WebSocket sẽ ngắt khi service ngủ; frontend có reconnect tự động.
- Chỉ chạy một backend instance. Nếu scale nhiều instance khi chưa có Redis hoặc
  database dùng chung, mỗi instance sẽ có một factory state khác nhau.
- Không dùng `NEXT_PUBLIC_DATA_SOURCE=mock` trên Vercel nếu muốn nhận dữ liệu BE.

## 8. Rollback và xử lý lỗi

- Frontend: Vercel > Deployments > chọn bản hoạt động tốt > **Promote to Production**.
- Backend: Render > Events/Deploys > chọn commit trước và redeploy.
- CORS error: kiểm tra `CORS_ORIGINS` khớp chính xác origin Vercel.
- REST chạy nhưng WebSocket lỗi: kiểm tra URL dùng `wss://`, không phải `ws://`.
- Frontend vẫn dùng URL cũ: cập nhật biến Vercel rồi redeploy frontend.
