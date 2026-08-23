# MVP nâng cao và trạng thái triển khai

Tài liệu này chốt phạm vi bám sát `TOPIC.md`. Vòng khép kín mục tiêu là:

```text
layout → Gazebo/ROS 2 → telemetry realtime → KPI → scenario comparison → approve → apply
```

Mock chỉ là fallback. MVP chỉ được xem là đạt khi acceptance path chạy được với
Gazebo/ROS 2 nhiều AMR và các mục bắt buộc dưới đây được đóng bằng code, test,
docs và CI.

## Ma trận yêu cầu

| Capability CORE | Trạng thái | Bằng chứng hiện có / phần còn thiếu |
|---|---|---|
| Khu vực nhà máy với vài robot mô phỏng | Một phần | Có Gazebo world/AMR nền tảng; cần chạy ổn định ít nhất 2 AMR |
| Vị trí và trạng thái realtime | Đạt MVP | REST cung cấp snapshot; WebSocket phát telemetry và event cập nhật |
| Giao diện giám sát | Đạt MVP | Factory page hiển thị telemetry realtime trên layout APPLIED; fallback layout chuẩn khi chưa apply |
| KPI authoritative | Đạt MVP | Scenario comparison hiển thị đủ chín KPI do Backend/SimPy tính |
| Cảnh báo bất thường | Đạt MVP | Có low battery, robot error, backlog, stale telemetry, bridge disconnect, command timeout và congestion lifecycle |
| Chạy và so sánh nhiều scenario | Đạt MVP | Scenario chọn layout version/route/config thật và có bounded optimization tối đa 64 candidate |
| Human-in-the-loop trước khi apply | Một phần | Có approve/reject/apply và RBAC; cần E2E Designer/Monitor với ROS apply |
| Thử thay đổi cấu hình vận hành | Đạt ở contract | Durable apply command có ACK/result/timeout/retry/audit và UI history; acceptance ROS thật còn ở M13 |
| Cho phép đổi bố trí và chạy lại | Đạt MVP | Designer CRUD layout, tạo version immutable và dùng version đó cho SimPy/apply |
| Giao diện 3D | Một phần | Có React Three Fiber scene nhưng route factory chính vẫn dùng 2D |
| Ít nhất hai vai trò Designer/Monitor | Đạt ở code | Supabase Auth, profile role và FastAPI guard đã có; chỉ cần E2E hai role |
| ROS2/Gazebo và đồng bộ hai chiều | Đạt ở code | Có multi-AMR, fleet/task lifecycle, bridge registry/telemetry và apply command ACK/result; còn hosted GCP acceptance |
| Tắc nghẽn mô phỏng | Một phần | Có waiting/backlog; cần zone occupancy/congestion score |
| Va chạm mô phỏng | Chưa có | Chỉ cần route conflict/no-go validation mức MVP, không cần physics nâng cao |
| Benchmark render và độ trễ realtime | Chưa có | Cần FPS, ROS-to-backend, backend-to-browser latency và dropped updates |
| Bảo mật telemetry/cấu hình | Đạt ở code | REST dùng Bearer JWT + profile DB; WebSocket xác thực token trước khi đăng ký broadcast; chỉ Monitor được đổi/reset factory |
| Persistence và telemetry history | Một phần | Scenario/audit/KPI đã có; còn layout, run, command, alert và telemetry partition/retention |

## Ranh giới triển khai hiện tại

Scenario benchmark trả lời câu hỏi về năng lực xử lý khi đổi số robot và các
tham số thời gian. Nó chưa đại diện cho mô phỏng vật lý hoặc tối ưu layout thật.

Khi apply scenario:

- `num_robots` được ánh xạ sang số robot của Mock Factory.
- `task_arrival_interval` được ánh xạ sang nhịp sinh task realtime.
- `num_tasks`, `travel_time`, `loading_time` và `simulation_time` chỉ dùng trong
  benchmark, không thay đổi chuyển động realtime.
- Factory được reset, vì vậy task, alert và KPI đang chạy sẽ bị xoá.

## Tiêu chí đóng MVP nâng cao

CORE chỉ hoàn thành khi người dùng có thể:

1. Chạy ít nhất hai AMR trong Gazebo/Nav2 và thấy telemetry qua bridge trên Digital Twin 3D.
2. Xem fleet, task, KPI và alert dùng cùng contract REST/WebSocket.
3. Chạy, lưu và so sánh scenario SimPy có layout, battery logistics và congestion.
4. Tạo/version layout, chạy scenario theo layout, submit, approve/reject và apply vào ROS2.
5. Phát hiện cảnh báo bất thường và báo cáo latency/FPS cơ bản.
6. Chứng minh RBAC, persistence cần thiết, ROS integration, frontend, container và deploy
   đều qua CI/build gate tương ứng.

Mock chỉ là chế độ phát triển/test, không thay thế acceptance criteria ROS2. MVP có
đúng hai role Designer/Monitor. Telemetry history cần thiết và retention thuộc MVP;
incident replay UI đầy đủ không phải acceptance bắt buộc.
