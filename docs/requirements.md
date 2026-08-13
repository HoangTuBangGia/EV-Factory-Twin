# Phạm vi và trạng thái MVP

Tài liệu này đối chiếu code hiện tại với đề tài trong `TOPIC.md`. Mục tiêu MVP
trước mắt là chứng minh một vòng khép kín an toàn:

```text
giám sát realtime → chạy scenario → so sánh KPI → phê duyệt/từ chối → apply
```

MVP hiện tại **không được mô tả là Digital Twin 3D/ROS2/Gazebo hoàn chỉnh**.

## Ma trận yêu cầu

| Yêu cầu theo đề tài | Trạng thái MVP | Bằng chứng hiện có / phần còn thiếu |
|---|---|---|
| Khu vực nhà máy với vài robot mô phỏng | Đạt MVP | Mock Factory có đội AMR, task, pin, trạng thái và layout cố định |
| Vị trí và trạng thái realtime | Đạt MVP | REST cung cấp snapshot; WebSocket phát telemetry và event cập nhật |
| Giao diện giám sát | Đạt MVP 2D | Dashboard và factory map SVG hiển thị robot; **chưa phải 3D/Three.js** |
| KPI throughput và cycle time | Đạt MVP | Backend realtime và benchmark SimPy đều trả KPI |
| Cảnh báo bất thường | Đạt MVP | Có alert cho pin thấp, robot chờ/lỗi, backlog và starvation |
| Chạy và so sánh nhiều scenario | Đạt MVP | Scenario API/UI chạy benchmark SimPy và so sánh candidate với baseline |
| Human-in-the-loop trước khi apply | Đạt guard MVP | Candidate phải `APPROVED` trước khi `APPLIED`; state chỉ ở RAM, chưa có danh tính người duyệt hoặc audit log |
| Thử thay đổi cấu hình vận hành | Một phần | Apply được số robot và nhịp sinh task vào mock realtime; chưa sửa hình học layout/route |
| Cho phép đổi bố trí và chạy lại | Chưa có | Chưa có layout editor, layout version, lưu draft hoặc mô phỏng theo geometry mới |
| Giao diện 3D | Chưa có | Factory view hiện là SVG 2D; chưa có Three.js/WebGL và model 3D |
| Ít nhất hai vai trò Designer/Monitor | Chưa có | Chưa có đăng nhập, RBAC hoặc bảo vệ route/API; nhãn giao diện không được xem là phân quyền |
| ROS2/Gazebo và đồng bộ hai chiều | Chưa có | Chưa có ROS2 node/bridge, topic, Gazebo world hoặc luồng command hai chiều |
| Tắc nghẽn/va chạm mô phỏng thực | Chưa có | SimPy dùng thời gian cố định và hàng chờ tài nguyên; chưa có route occupancy, collision hay no-go validation |
| Benchmark render và độ trễ realtime | Chưa có | Chưa đo FPS, dropped frames, telemetry latency hoặc giới hạn số robot |
| Bảo mật telemetry/cấu hình | Chưa có | Chưa có authentication, authorization hoặc quản lý secret/quyền sửa cấu hình |
| Lưu telemetry, KPI và lịch sử duyệt | Chưa có | State scenario và factory nằm trong RAM; restart backend sẽ mất dữ liệu |

## Ranh giới MVP hiện tại

Scenario benchmark trả lời câu hỏi về năng lực xử lý khi đổi số robot và các
tham số thời gian. Nó chưa đại diện cho mô phỏng vật lý hoặc tối ưu layout thật.

Khi apply scenario:

- `num_robots` được ánh xạ sang số robot của Mock Factory.
- `task_arrival_interval` được ánh xạ sang nhịp sinh task realtime.
- `num_tasks`, `travel_time`, `loading_time` và `simulation_time` chỉ dùng trong
  benchmark, không thay đổi chuyển động realtime.
- Factory được reset, vì vậy task, alert và KPI đang chạy sẽ bị xoá.

## Tiêu chí demo MVP

MVP được xem là demo được khi người dùng có thể:

1. Mở dashboard 2D và thấy robot cập nhật realtime từ backend.
2. Xem fleet, task, KPI và alert dùng cùng contract REST/WebSocket.
3. Chạy một candidate scenario hợp lệ và nhận KPI benchmark.
4. So sánh candidate với baseline.
5. Chứng minh apply trước approve bị chặn.
6. Approve rồi apply thành công, sau đó thấy factory reset với cấu hình được hỗ
   trợ.

Các hạng mục 3D, layout editor, ROS2/Gazebo, authentication, database và
congestion/collision vật lý là công việc sau MVP, không được tuyên bố là đã hoàn
thành trong bản demo hiện tại.
