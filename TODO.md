# Roadmap Login, RBAC, Supabase và Audit Log

Mục tiêu: bổ sung đăng nhập và phân quyền thật cho Factory Twin mà không làm hỏng
luồng realtime/scenario hiện có. Hai role nghiệp vụ bắt buộc là `DESIGNER` và
`MONITOR`; `ADMIN` chỉ là role quản trị kỹ thuật, không được tính là người dùng
nghiệp vụ thứ ba.

Nguyên tắc triển khai:

- Làm tuần tự theo từng phase; chỉ chuyển phase khi checkpoint của phase trước pass.
- Không lưu password trong bảng tự tạo; Supabase Auth quản lý danh tính và password.
- Không cho người dùng chọn role trên form login; backend/database quyết định role.
- Không chỉ ẩn nút ở frontend; FastAPI phải trả `401/403` khi không đủ quyền.
- Không đưa `SUPABASE_SERVICE_ROLE_KEY` hoặc database URL bí mật vào frontend.
- Chưa lưu raw telemetry 10 Hz và chưa bật TimescaleDB trong MVP này.
- Mọi thay đổi schema phải đi qua migration và được commit vào repository.

## 0. Chốt phạm vi và permission matrix

- [x] Xác nhận hai role nghiệp vụ:
  - `DESIGNER`: thiết kế/chạy scenario và chỉnh layout sau này.
  - `MONITOR`: giám sát, review, approve/reject và apply scenario.
- [x] Xác nhận `DESIGNER` không được tự approve/apply scenario.
- [x] Xác nhận `MONITOR` không được tạo hoặc chạy scenario.
- [x] Xác nhận `ADMIN` chỉ quản lý user/role/audit, không mặc định có quyền vận hành.
- [x] Xác nhận hệ thống nội bộ: không có public sign-up trong MVP.
- [x] Xác nhận ba tài khoản demo cần tạo: một Designer, một Monitor, một Admin.
- [x] Chốt thời gian session và hành vi khi session hết hạn.
- [x] Chốt WebSocket sẽ xác thực bằng access token gửi ở message đầu tiên.

Permission matrix mục tiêu:

| Chức năng | DESIGNER | MONITOR | ADMIN |
|---|---:|---:|---:|
| Xem robot/task/KPI/alert | Có | Có | Có |
| Tạo và chạy scenario | Có | Không | Không mặc định |
| Xem kết quả scenario | Có | Có | Có |
| Approve/Reject scenario | Không | Có | Không mặc định |
| Apply scenario | Không | Có | Không mặc định |
| Start/Stop/Reset MockFactory | Không | Có | Không mặc định |
| Chỉnh layout sau này | Có | Không | Không mặc định |
| Tạo/khóa user và đổi role | Không | Không | Có |
| Xem audit log | Không | Không | Có |

### Checkpoint phase 0

- [x] Team duyệt permission matrix.
- [x] Không còn endpoint nhạy cảm nào chưa xác định owner/role.

## 1. Khởi tạo Supabase và quản lý môi trường

- [ ] Tạo Supabase project cho development.
- [ ] Bật Email/Password authentication.
- [ ] Tắt public sign-up hoặc chỉ cho admin mời/tạo tài khoản.
- [ ] Ghi lại Project URL, publishable/anon key, JWT issuer và thông tin JWKS.
- [ ] Thêm Supabase CLI/config nếu team chọn quản lý local migration bằng CLI.
- [ ] Tạo thư mục migration, ví dụ `supabase/migrations/`.
- [ ] Thêm biến frontend vào `.env.example`:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- [ ] Thêm biến backend vào `apps/backend/.env.example`:
  - `SUPABASE_URL`
  - `SUPABASE_JWT_ISSUER`
  - `SUPABASE_JWKS_URL`
  - `SUPABASE_SERVICE_ROLE_KEY` nếu backend thực sự cần admin API.
- [ ] Xác nhận secret thật bị `.gitignore` và không xuất hiện trong Git history/log.
- [ ] Ghi rõ biến nào an toàn ở frontend và biến nào chỉ được dùng ở backend.

### Checkpoint phase 1

- [ ] Frontend đọc được publishable key từ môi trường.
- [ ] Backend đọc được cấu hình Supabase mà không log secret.
- [ ] Không có service-role key trong bundle frontend.

## 2. Thiết kế database user/profile/role

- [ ] Tạo enum `app_role`: `DESIGNER`, `MONITOR`, `ADMIN`.
- [ ] Tạo bảng `public.profiles`:
  - `id uuid primary key references auth.users(id) on delete cascade`
  - `display_name text not null`
  - `role app_role not null`
  - `is_active boolean not null default true`
  - `created_at timestamptz`
  - `updated_at timestamptz`
- [ ] Tạo trigger thêm profile khi admin tạo user, hoặc tạo profile trong cùng service.
- [ ] Bảo đảm trigger lỗi không để lại user/profile ở trạng thái không nhất quán.
- [ ] Bật RLS cho `profiles`.
- [ ] Policy: user được đọc profile của chính mình.
- [ ] Policy: user thường không được tự thay đổi `role` hoặc `is_active`.
- [ ] Policy/service: chỉ Admin được thay đổi role/trạng thái tài khoản.
- [ ] Tạo index cần thiết cho `role` và `is_active` nếu có truy vấn danh sách user.
- [ ] Viết migration rollback hoặc hướng dẫn rollback an toàn.
- [ ] Seed/tạo ba tài khoản demo bằng Dashboard hoặc script chạy phía server.

### Checkpoint phase 2

- [ ] Login Supabase trả đúng `auth.users.id`.
- [ ] Mỗi demo user có đúng một profile và role.
- [ ] User không thể tự nâng role bằng Supabase client/REST.
- [ ] RLS test cho phép/không cho phép đúng các trường hợp trên.

## 3. Authentication contract cho FastAPI

- [ ] Thiết kế model `CurrentUser` tối thiểu:
  - `id`
  - `email`
  - `display_name`
  - `role`
  - `is_active`
- [ ] Viết dependency `get_current_user`.
- [ ] Xác minh JWT bằng issuer, audience/signature và expiry; không chỉ decode payload.
- [ ] Tải profile/role từ nguồn tin cậy; không tin role do frontend gửi lên.
- [ ] Từ chối user bị khóa bằng `403`.
- [ ] Chuẩn hóa lỗi:
  - thiếu/sai/hết hạn token → `401`
  - đúng token nhưng sai role → `403`
  - sai state transition scenario → `409`
- [ ] Thêm `GET /api/v1/auth/me` trả profile hiện tại.
- [ ] Viết helper/dependency `require_roles(...)` hoặc `require_permission(...)`.
- [ ] Không dùng service-role key để bỏ qua mọi kiểm tra nghiệp vụ.

### Checkpoint phase 3

- [ ] Token hợp lệ gọi `/auth/me` thành công.
- [ ] Token hết hạn/sai chữ ký trả `401`.
- [ ] User inactive trả `403`.
- [ ] Unit test dependency không phụ thuộc network Supabase thật.

## 4. Bảo vệ API theo role

- [ ] Cho cả `DESIGNER` và `MONITOR` đọc robot/task/KPI/alert/factory.
- [ ] Chỉ `DESIGNER` gọi được `POST /api/v1/scenarios/run`.
- [ ] Chỉ `MONITOR` gọi được approve/reject/apply.
- [ ] Chỉ `MONITOR` gọi được mock start/stop/reset/config.
- [ ] Giữ server-side guard: chỉ `APPROVED` mới được apply.
- [ ] Kiểm tra role trước khi thực hiện side effect/reset factory.
- [ ] Quyết định quyền đọc danh sách scenario của Designer và Monitor.
- [ ] Viết test matrix `200/401/403/409` cho từng endpoint nhạy cảm.
- [ ] Kiểm tra Swagger/OpenAPI mô tả Bearer authentication đúng.

### Checkpoint phase 4

- [ ] Designer run được nhưng approve/apply nhận `403`.
- [ ] Monitor xem/review/apply được nhưng run nhận `403`.
- [ ] Người chưa login không gọi được API được bảo vệ.
- [ ] Không có endpoint mock/scenario mutation bị bỏ sót authorization.

## 5. Session và middleware trong Next.js

- [ ] Cài và cấu hình Supabase client theo mô hình session đã chọn.
- [ ] Ưu tiên cookie/session hỗ trợ SSR thay vì tự lưu password/token tùy tiện.
- [ ] Tạo client dùng trong browser và client dùng phía server/middleware riêng biệt.
- [ ] Viết middleware/proxy bảo vệ route dashboard.
- [ ] Route public: `/login`.
- [ ] Route authenticated: `/`, `/factory`, `/fleet`, `/tasks`, `/analytics`, `/scenarios`.
- [ ] Route admin tương lai: `/admin/*` chỉ cho `ADMIN`.
- [ ] Người chưa login được redirect về `/login` và giữ `returnTo` an toàn.
- [ ] Người đã login mở `/login` được redirect về trang phù hợp.
- [ ] Refresh session/cookie đúng và không tạo redirect loop.
- [ ] Thêm `Cache-Control: private, no-store` cho response xử lý auth nếu cần.
- [ ] Middleware chỉ phục vụ route/UX; không thay thế authorization của FastAPI.

### Checkpoint phase 5

- [ ] Mở dashboard khi chưa login bị chuyển về `/login`.
- [ ] Refresh vẫn giữ phiên hợp lệ.
- [ ] Session hết hạn đưa về login với thông báo rõ ràng.
- [ ] Không có redirect loop trên local và Vercel preview.

## 6. Trang Login và auth state frontend

- [ ] Thiết kế trang `/login` nhất quán với giao diện Factory Twin.
- [ ] Form chỉ có email/username và password; không có dropdown chọn role.
- [ ] Có loading state khi submit.
- [ ] Có lỗi sai tài khoản/mật khẩu.
- [ ] Có lỗi backend/Supabase không khả dụng.
- [ ] Không phân biệt “email tồn tại” và “password sai” trong thông báo công khai.
- [ ] Thiết kế auth store/context riêng, không trộn vào `factory-store`.
- [ ] Auth state có `user`, `session`, `isLoading`, `login`, `logout`.
- [ ] Sau login điều hướng:
  - Designer → `/scenarios` hoặc trang đã lưu trong `returnTo`.
  - Monitor → `/` hoặc trang đã lưu trong `returnTo`.
  - Admin → `/admin` khi trang admin đã tồn tại; trước mắt có thể về `/`.
- [ ] Logout xóa session, đóng WebSocket và đưa về `/login`.
- [ ] Topbar hiển thị tên, role và nút logout thay chữ `Designer` hard-code.

### Checkpoint phase 6

- [ ] Ba tài khoản demo login/logout thành công.
- [ ] Login sai hiển thị lỗi và không tạo session.
- [ ] Refresh không làm mất session.
- [ ] Topbar hiển thị đúng user/role từ backend hoặc Supabase session.

## 7. UI theo role

- [ ] Tạo helper `can(permission)` hoặc permission map dùng chung trong frontend.
- [ ] Designer thấy form và nút `Run benchmark`.
- [ ] Designer không thấy hoặc không dùng được Approve/Reject/Apply.
- [ ] Monitor xem cấu hình/KPI ở chế độ read-only.
- [ ] Monitor thấy Approve/Reject và chỉ thấy Apply khi scenario đã approved.
- [ ] Hiển thị “Waiting for monitor review” sau khi Designer chạy scenario.
- [ ] Sidebar ẩn route/action không liên quan đến role.
- [ ] Không dùng việc ẩn nút làm bằng chứng duy nhất của authorization.
- [ ] Có trang `403 Forbidden` hoặc thông báo đủ quyền rõ ràng.
- [ ] Không hiển thị nhãn role giả khi chưa có session.

### Checkpoint phase 7

- [ ] Demo hai cửa sổ/trình duyệt: Designer tạo scenario, Monitor duyệt và apply.
- [ ] Thay URL hoặc gọi API thủ công vẫn bị backend chặn đúng quyền.

## 8. Xác thực WebSocket

- [ ] Không thêm connection vào broadcast pool trước khi xác thực thành công.
- [ ] Frontend gửi access token làm message đầu tiên sau khi socket mở.
- [ ] Backend xác minh token và user active trước khi phát telemetry.
- [ ] Token sai/hết hạn: đóng socket bằng close code phù hợp và không phát dữ liệu.
- [ ] Khi access token refresh, WebSocket reconnect bằng token mới.
- [ ] Logout phải đóng socket và hủy reconnect timer.
- [ ] Reconnect thành công phải tải lại REST snapshot robot/task/KPI/alert.
- [ ] Không đưa access token vào log hoặc thông báo lỗi.
- [ ] Viết test cho socket hợp lệ, token sai, token hết hạn và reconnect.

### Checkpoint phase 8

- [ ] Client chưa xác thực không nhận telemetry.
- [ ] Designer và Monitor hợp lệ đều nhận realtime.
- [ ] Backend restart → frontend reconnect, refetch snapshot và trở lại `LIVE`.

## 9. Business audit log

- [ ] Tạo bảng `audit_events`:
  - `id`
  - `actor_id`
  - `action`
  - `resource_type`
  - `resource_id`
  - `before_data jsonb`
  - `after_data jsonb`
  - `request_id`
  - `created_at`
- [ ] Chỉ backend/service tin cậy được insert audit event.
- [ ] User thường không được update/delete audit event.
- [ ] Ghi log tối thiểu cho:
  - `SCENARIO_CREATED` hoặc `SCENARIO_RUN`
  - `SCENARIO_APPROVED`
  - `SCENARIO_REJECTED`
  - `SCENARIO_APPLIED`
  - `FACTORY_RESET`
  - `ROLE_CHANGED`
  - `USER_DISABLED`
- [ ] Thêm `created_by`, `reviewed_by`, `applied_by` vào scenario hoặc review record.
- [ ] Ghi trước/sau cho thay đổi cấu hình quan trọng.
- [ ] Không ghi access token, password hoặc secret vào audit data.
- [ ] Phân biệt business audit table với log kỹ thuật/pgAudit.
- [ ] Cân nhắc bật pgAudit sau MVP; không dùng nó thay business audit log.

### Checkpoint phase 9

- [ ] Có thể trả lời ai tạo, ai duyệt, ai apply và thời điểm thực hiện.
- [ ] Audit record không thể bị sửa/xóa bởi Designer hoặc Monitor.
- [ ] Admin đọc được audit log theo thời gian và resource.

## 10. Persist scenario vào PostgreSQL

- [ ] Thiết kế bảng `scenarios` tương thích contract hiện tại.
- [ ] Lưu config và metrics dưới cột có kiểu rõ ràng hoặc JSONB có schema/version.
- [ ] Lưu status, duration, timestamps và actor IDs.
- [ ] Tạo index cho status, created_at, created_by và reviewed_by.
- [ ] Thay in-memory scenario repository bằng database repository.
- [ ] Giữ service state transition độc lập khỏi ORM/database details.
- [ ] Dùng transaction cho approve/reject/apply và audit event liên quan.
- [ ] Chống hai Monitor approve/apply đồng thời bằng lock/version/conditional update.
- [ ] Restart backend không làm mất scenario.
- [ ] UI tải lại candidate/list scenario sau refresh.
- [ ] Viết migration dữ liệu nếu contract thay đổi.

### Checkpoint phase 10

- [ ] Run → restart backend → scenario vẫn tồn tại.
- [ ] Refresh trang vẫn tiếp tục được workflow.
- [ ] Chỉ một transition thắng khi có request đồng thời.
- [ ] Apply và audit log nhất quán khi có lỗi.

## 11. Superadmin — làm sau khi login/RBAC ổn định

- [ ] Tạo route `/admin/users`.
- [ ] Chỉ `ADMIN` truy cập được cả frontend và backend API.
- [ ] Danh sách user không trả password/hash/token.
- [ ] Admin mời/tạo user qua server-side admin API.
- [ ] Admin gán `DESIGNER` hoặc `MONITOR`.
- [ ] Admin khóa/mở tài khoản.
- [ ] Không cho admin tự xóa/khóa tài khoản admin cuối cùng.
- [ ] Mọi thay đổi role/trạng thái user đều có audit event.
- [ ] Bật MFA cho tài khoản Admin trước production.
- [ ] Không expose Supabase service-role key ở browser.

### Checkpoint phase 11

- [ ] Designer/Monitor không truy cập được `/admin` hoặc admin API.
- [ ] Admin quản lý user được nhưng không tự động có quyền apply scenario.
- [ ] Role change có hiệu lực theo chính sách refresh/revoke session đã chọn.

## 12. Telemetry, PostgreSQL và TimescaleDB — chưa chặn MVP auth

- [ ] Chỉ lưu dữ liệu cần truy vấn/lịch sử:
  - scenario và review;
  - task transition;
  - alert;
  - KPI snapshot;
  - layout/version sau này.
- [ ] Không lưu toàn bộ robot telemetry 10 Hz trong phase đầu.
- [ ] Nếu cần position history, downsample còn 5–10 giây/mẫu/robot.
- [ ] Xác định retention cho KPI/position history.
- [ ] Đo số row/ngày và dung lượng trước khi chọn time-series engine.
- [ ] Dùng PostgreSQL thường/index/partition trước nếu tải còn nhỏ.
- [ ] Không bật TimescaleDB trên Supabase nếu version/extension không còn được hỗ trợ.
- [ ] Chỉ đánh giá dedicated TimescaleDB/Timescale Cloud hoặc ClickHouse khi tải thật
      chứng minh PostgreSQL hiện tại không đủ.
- [ ] Viết job aggregate/xóa dữ liệu cũ nếu bắt đầu lưu telemetry history.

### Checkpoint phase 12

- [ ] Có số liệu insert rate, storage/day và query latency.
- [ ] Quyết định time-series dựa trên đo đạc, không chỉ dựa trên tên công nghệ.

## 13. Test, CI và demo acceptance

- [ ] Unit test auth store và login form.
- [ ] Unit test JWT verification và `require_roles`.
- [ ] Integration test API permission matrix.
- [ ] Test RLS bằng user token của từng role.
- [ ] Test WebSocket authentication/reconnect.
- [ ] Browser E2E:
  1. Designer login.
  2. Designer chạy scenario.
  3. Designer bị chặn approve/apply.
  4. Monitor login.
  5. Monitor review, approve và apply.
  6. Factory reset và dashboard cập nhật.
  7. Audit log có đủ actor/action/time.
- [ ] Test refresh giữa các bước.
- [ ] Test session hết hạn.
- [ ] Test user bị Admin khóa khi đang có session.
- [ ] Test trên kích thước laptop demo.
- [ ] Cập nhật CI với migration/schema/RLS tests cần thiết.
- [ ] Chạy `make check`.
- [ ] Chạy frontend lint, test và production build.
- [ ] Chạy `git diff --check` và bảo đảm migration được track.
- [ ] Quay video dự phòng cho luồng hai role.

## Definition of Done

- [ ] Không thể mở dashboard khi chưa đăng nhập.
- [ ] Login, refresh session và logout hoạt động ổn định.
- [ ] Role được lấy từ database/backend, không lấy từ input frontend.
- [ ] Designer run scenario nhưng không approve/apply được.
- [ ] Monitor approve/reject/apply nhưng không run scenario được.
- [ ] Backend trả đúng `401`, `403`, `409`.
- [ ] WebSocket không phát telemetry trước khi xác thực.
- [ ] Reconnect tải lại snapshot và không giữ state cũ sai lệch.
- [ ] Scenario lưu được qua backend restart và refresh frontend.
- [ ] Audit log ghi đúng người tạo, duyệt và apply.
- [ ] Admin quản lý user/role mà không lộ service-role key.
- [ ] RLS bật trên mọi bảng được expose.
- [ ] Không lưu raw telemetry 10 Hz trong MVP.
- [ ] Test, CI và browser E2E đều xanh.


# tutorial quay demo

Với phiên bản hiện tại, video 3 phút nên kể một câu chuyện rất rõ:

> Theo dõi nhà máy realtime → thử cấu hình tối ưu → người có thẩm quyền phê duyệt → áp dụng và thấy nhà máy thay đổi.

## Kịch bản quay đề xuất

| Thời gian | Hình ảnh/thao tác | Lời thoại gợi ý |
|---|---|---|
| 0:00–0:15 | Title ngắn: “EV Factory Digital Twin” rồi chuyển ngay vào dashboard | “Trong nhà máy pin EV, việc thay đổi số lượng robot có thể ảnh hưởng trực tiếp đến throughput, thời gian chờ và backlog. Giải pháp của chúng tôi cho phép theo dõi và thử nghiệm cấu hình trước khi áp dụng.” |
| 0:15–0:45 | Mở **Factory view**. Cho thấy trạng thái `LIVE`, robot đang di chuyển và KPI cập nhật | “Đây là Digital Twin của hệ thống vận chuyển nội bộ. Dữ liệu telemetry được cập nhật realtime, giúp theo dõi vị trí, trạng thái và hiệu suất của toàn bộ đội robot.” |
| 0:45–1:00 | Click một robot để mở detail drawer | “Người vận hành có thể xem pin, tốc độ, tọa độ, nhiệm vụ và payload của từng robot.” |
| 1:00–1:35 | Sang **Scenarios**, đăng nhập/quay dưới role **Designer**. Nhập scenario với số robot khác baseline và bấm Run | “Trước khi thay đổi nhà máy, Designer tạo một candidate scenario. Hệ thống sử dụng mô phỏng SimPy để benchmark cấu hình mới với baseline.” |
| 1:35–1:55 | Zoom vào bảng so sánh KPI: throughput, cycle time, waiting time, backlog/completion rate | “Kết quả cho biết cấu hình mới cải thiện throughput và thời gian chờ như thế nào, giúp quyết định dựa trên số liệu thay vì thử trực tiếp trên hệ thống thật.” |
| 1:55–2:15 | Cho thấy Designer không có nút Approve/Apply hoặc thông báo bị chặn | “Designer chỉ được phép chạy thử nghiệm. Việc phê duyệt và áp dụng được tách riêng để tránh một cá nhân tự thay đổi cấu hình vận hành.” |
| 2:15–2:40 | Chuyển sang phiên **Monitor** đã đăng nhập sẵn. Mở đúng scenario → Approve → Apply to factory | “Monitor kiểm tra kết quả, phê duyệt, sau đó áp dụng cấu hình. Backend đồng thời kiểm tra role và trạng thái scenario, nên một cấu hình chưa được approve không thể được áp dụng.” |
| 2:40–2:52 | Quay lại Factory view, cho thấy số robot/config đã thay đổi | “Sau khi áp dụng, factory được reset theo cấu hình mới và dashboard tiếp tục nhận telemetry realtime.” |
| 2:52–3:00 | Mở nhanh audit log hoặc kết bằng màn hình Factory | “Mọi hành động đều lưu actor, thời gian và nội dung thay đổi để có thể truy vết. Đây là nền tảng cho việc kết nối ROS2 và mô phỏng vật lý trong giai đoạn tiếp theo.” |

## Cách quay để video trông chuyên nghiệp

Chuẩn bị hai cửa sổ hoặc hai browser profile trước khi quay:

- Cửa sổ 1: đăng nhập sẵn bằng **Designer**.
- Cửa sổ 2: đăng nhập sẵn bằng **Monitor**.
- Mỗi cửa sổ mở đúng trang cần dùng.
- Tạo trước một scenario “Baseline”; khi quay chỉ tạo candidate.
- Nếu kết quả mô phỏng có độ trễ, có thể cắt khoảng chờ thay vì để người xem nhìn loading.
- Dùng scenario có thay đổi dễ thấy, chẳng hạn từ 3 lên 5 hoặc 6 robot.

Thiết lập quay:

- Độ phân giải 1920×1080, 30 fps.
- Browser zoom khoảng 90–100%; đóng bookmark bar và notification.
- Chỉ quay vùng trình duyệt, không quay desktop lộn xộn.
- Di chuột chậm, dừng khoảng 1 giây trước khi click.
- Zoom hậu kỳ nhẹ vào KPI, role và nút Approve/Apply.
- Thu voice-over sau khi quay màn hình sẽ ít lỗi và dễ căn đúng 3 phút hơn.
- Nhạc nền rất nhỏ; giọng nói phải rõ hơn nhạc nhiều lần.
- Che email, access token, URL nội bộ và thông tin Supabase nếu xuất hiện.

## Điểm cần nhấn mạnh

| Thời gian | Hình ảnh/thao tác | Lời thoại gợi ý |
|---|---|---|
| 0:00–0:15 | Title ngắn: “EV Factory Digital Twin” rồi chuyển ngay vào dashboard | “Trong nhà máy pin EV, việc thay đổi số lượng robot có thể ảnh hưởng trực tiếp đến throughput, thời gian chờ và backlog. Giải pháp của chúng tôi cho phép theo dõi và thử nghiệm cấu hình trước khi áp dụng.” |
| 0:15–0:45 | Mở **Factory view**. Cho thấy trạng thái `LIVE`, robot đang di chuyển và KPI cập nhật | “Đây là Digital Twin của hệ thống vận chuyển nội bộ. Dữ liệu telemetry được cập nhật realtime, giúp theo dõi vị trí, trạng thái và hiệu suất của toàn bộ đội robot.” |
| 0:45–1:00 | Click một robot để mở detail drawer | “Người vận hành có thể xem pin, tốc độ, tọa độ, nhiệm vụ và payload của từng robot.” |
| 1:00–1:35 | Sang **Scenarios**, đăng nhập/quay dưới role **Designer**. Nhập scenario với số robot khác baseline và bấm Run | “Trước khi thay đổi nhà máy, Designer tạo một candidate scenario. Hệ thống sử dụng mô phỏng SimPy để benchmark cấu hình mới với baseline.” |
| 1:35–1:55 | Zoom vào bảng so sánh KPI: throughput, cycle time, waiting time, backlog/completion rate | “Kết quả cho biết cấu hình mới cải thiện throughput và thời gian chờ như thế nào, giúp quyết định dựa trên số liệu thay vì thử trực tiếp trên hệ thống thật.” |
| 1:55–2:15 | Cho thấy Designer không có nút Approve/Apply hoặc thông báo bị chặn | “Designer chỉ được phép chạy thử nghiệm. Việc phê duyệt và áp dụng được tách riêng để tránh một cá nhân tự thay đổi cấu hình vận hành.” |
| 2:15–2:40 | Chuyển sang phiên **Monitor** đã đăng nhập sẵn. Mở đúng scenario → Approve → Apply to factory | “Monitor kiểm tra kết quả, phê duyệt, sau đó áp dụng cấu hình. Backend đồng thời kiểm tra role và trạng thái scenario, nên một cấu hình chưa được approve không thể được áp dụng.” |
| 2:40–2:52 | Quay lại Factory view, cho thấy số robot/config đã thay đổi | “Sau khi áp dụng, factory được reset theo cấu hình mới và dashboard tiếp tục nhận telemetry realtime.” |
| 2:52–3:00 | Mở nhanh audit log hoặc kết bằng màn hình Factory | “Mọi hành động đều lưu actor, thời gian và nội dung thay đổi để có thể truy vết. Đây là nền tảng cho việc kết nối ROS2 và mô phỏng vật lý trong giai đoạn tiếp theo.” |