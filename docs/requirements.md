# Phạm vi CORE và trạng thái triển khai

Tài liệu này đối chiếu code hiện tại với phạm vi CORE trong `AGENTS.md` và
`docs/architecture.md`. Vòng khép kín mục tiêu là:

```text
giám sát realtime → chạy scenario → so sánh KPI → phê duyệt/từ chối → apply
```

Hệ thống hiện có một MVP mock; dự án chỉ được xem là hoàn thành CORE khi các mục
`Chưa có` và `Một phần` dưới đây được đóng bằng code, test, docs và CI.

## Ma trận yêu cầu

| Capability CORE | Trạng thái | Bằng chứng hiện có / phần còn thiếu |
|---|---|---|
| Khu vực nhà máy với vài robot mô phỏng | Đạt MVP | Mock Factory có đội AMR, task, pin, trạng thái và layout cố định |
| Vị trí và trạng thái realtime | Đạt MVP | REST cung cấp snapshot; WebSocket phát telemetry và event cập nhật |
| Giao diện giám sát | Một phần | Dashboard có 2D và scene Three.js thử nghiệm; cần hợp nhất thành Digital Twin realtime được kiểm thử trên desktop/mobile |
| KPI throughput và cycle time | Đạt MVP | Backend realtime và benchmark SimPy đều trả KPI |
| Cảnh báo bất thường | Đạt MVP | Có alert cho pin thấp, robot chờ/lỗi, backlog và starvation |
| Chạy và so sánh nhiều scenario | Đạt MVP | Scenario API/UI chạy benchmark SimPy và so sánh candidate với baseline |
| Human-in-the-loop trước khi apply | Đạt ở code | Candidate phải `APPROVED` trước khi `APPLIED`; Designer/Monitor tách quyền; scenario lưu actor/timestamp/version và business audit. Còn cần browser E2E với ba tài khoản hosted |
| Thử thay đổi cấu hình vận hành | Một phần | Apply được số robot và nhịp sinh task vào mock realtime; chưa sửa hình học layout/route |
| Cho phép đổi bố trí và chạy lại | Chưa có | Chưa có layout editor, layout version, lưu draft hoặc mô phỏng theo geometry mới |
| Giao diện 3D | Một phần | Đã có React Three Fiber scene nhưng route factory vẫn dùng 2D và chưa có Playwright/canvas regression gate |
| Ít nhất hai vai trò Designer/Monitor | Đạt ở code | Supabase Auth, profile role từ PostgreSQL, FastAPI guard và UI theo role đã có; còn cần tạo và chạy thử ba tài khoản demo thật |
| ROS2/Gazebo và đồng bộ hai chiều | Chưa có | Chưa có ROS2 node/bridge, topic, Gazebo world hoặc luồng command hai chiều |
| Tắc nghẽn/va chạm mô phỏng thực | Chưa có | SimPy dùng thời gian cố định và hàng chờ tài nguyên; chưa có route occupancy, collision hay no-go validation |
| Benchmark render và độ trễ realtime | Chưa có | Chưa đo FPS, dropped frames, telemetry latency hoặc giới hạn số robot |
| Bảo mật telemetry/cấu hình | Đạt ở code | REST dùng Bearer JWT + profile DB; WebSocket xác thực token trước khi đăng ký broadcast; chỉ Monitor được đổi/reset factory |
| Lưu telemetry, KPI và lịch sử duyệt | Một phần | Scenario/audit lưu PostgreSQL; KPI được snapshot mỗi 10 giây wall-clock khi có DB; raw telemetry 10 Hz chủ động không lưu; factory realtime vẫn ở RAM |

## Ranh giới triển khai hiện tại

Scenario benchmark trả lời câu hỏi về năng lực xử lý khi đổi số robot và các
tham số thời gian. Nó chưa đại diện cho mô phỏng vật lý hoặc tối ưu layout thật.

Khi apply scenario:

- `num_robots` được ánh xạ sang số robot của Mock Factory.
- `task_arrival_interval` được ánh xạ sang nhịp sinh task realtime.
- `num_tasks`, `travel_time`, `loading_time` và `simulation_time` chỉ dùng trong
  benchmark, không thay đổi chuyển động realtime.
- Factory được reset, vì vậy task, alert và KPI đang chạy sẽ bị xoá.

## Tiêu chí đóng CORE

CORE chỉ hoàn thành khi người dùng có thể:

1. Chạy ít nhất hai AMR trong Gazebo/Nav2 và thấy telemetry qua bridge trên Digital Twin.
2. Xem fleet, task, KPI và alert dùng cùng contract REST/WebSocket.
3. Lưu và replay telemetry lịch sử qua cùng contract realtime.
4. Chạy, lưu và so sánh scenario SimPy có battery logistics, charging và congestion.
5. Tạo/version layout, chạy scenario theo layout, submit, approve/reject và apply.
6. Chứng minh RBAC, persistence, ROS integration, frontend, container và deploy
   đều qua CI/build gate tương ứng.

MVP mock vẫn là chế độ phát triển hợp lệ nhưng không thay thế acceptance criteria
CORE. Hosted RBAC chỉ hoàn thành sau khi RLS và browser E2E chạy với ba role thật.
