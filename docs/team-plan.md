# Team Plan: ROS2 MVP nâng cao

## Mục tiêu

Hoàn thành vertical slice bám sát `TOPIC.md`:

```text
Layout → SimPy/Gazebo → ROS2 telemetry → FastAPI → WebSocket → 3D
                                      ↓
                              KPI/alert/latency
                                      ↓
                            approve → apply command
```

## Phân công bốn người

### Người 1: ROS2/Gazebo và edge runtime

Phụ trách `ros2_ws`.

- Hoàn thiện world Gazebo và ít nhất hai AMR có namespace riêng.
- Publish odometry, battery, status và task state.
- Hoàn thiện launch file chạy toàn bộ edge stack.
- Thêm fleet/task manager tối giản nhận command từ backend.
- Publish kết quả command, timeout và lỗi bất thường.
- Viết ROS unit/integration tests và tài liệu chạy edge.

Đầu ra:

- `ros2 launch amr_gazebo sim.launch.py` chạy được 2 AMR.
- Backend command đi tới ROS2 và có acknowledgement.
- Bridge gửi telemetry chuẩn hóa cho từng AMR.

### Người 2: Backend, contract và deployment API

Phụ trách `apps/backend`, `packages/twin-core`, API và Render.

- Giữ canonical telemetry contract dùng chung cho mock và ROS2.
- Thêm command gateway từ FastAPI tới edge gateway/fleet manager.
- Thêm layout/version/config API.
- Gắn scenario với layout và apply candidate vào ROS2 runtime.
- Thêm stale telemetry, command timeout và ROS disconnect alerts.
- Giữ RBAC tối thiểu cho `DESIGNER` và `MONITOR`.
- Đóng Dockerfile, Render service và smoke check.

Đầu ra:

- REST/WebSocket API chạy trên Render.
- Apply chỉ chạy với scenario đã approved.
- API không mở ROS DDS trực tiếp ra Internet.

### Người 3: Frontend 3D và trải nghiệm demo

Phụ trách `apps/frontend`.

- Đưa `FactoryScene` vào factory page chính.
- Hiển thị pose, orientation, velocity, battery, task, route và alert realtime.
- Tạo layout editor tối giản bằng form hoặc canvas 2D nhẹ.
- Hiển thị baseline/candidate KPI comparison.
- Hiển thị connection state, telemetry timestamp và latency.
- Implement Designer/Monitor permissions ở UI, nhưng không thay thế backend guard.
- Đóng Vercel build và Playwright smoke flow.

Đầu ra:

- Một màn hình factory 3D dùng được trên desktop/mobile.
- Luồng demo: chỉnh layout → chạy → compare → approve → apply → monitor.

### Người 4: Simulation, KPI, benchmark và tích hợp

Phụ trách `services/simulation`, `evaluation`, integration tests và release evidence.

- Cho layout làm input thật của SimPy.
- Bổ sung congestion score dựa trên zone occupancy/waiting.
- Giữ throughput, cycle time, waiting, completion và delivery delay.
- Tạo baseline/candidate fixtures có kết quả khác nhau.
- Đo ROS-to-backend, backend-to-browser latency và FPS cơ bản.
- Viết integration test cho ROS → backend → WebSocket → frontend contract.
- Chạy full quality gates và gom evidence cho demo.

Đầu ra:

- Báo cáo so sánh scenario theo layout.
- Báo cáo latency/FPS.
- Test end-to-end và checklist acceptance.

## Thứ tự làm việc

1. Người 1 khóa ROS topics, namespaces và command contract.
2. Người 2 khóa canonical API và edge gateway contract.
3. Người 4 dùng cùng contract để nối SimPy/layout/KPI.
4. Người 3 nối frontend 3D và scenario workflow.
5. Cả team chạy integration trên edge thật hoặc VM Ubuntu.
6. Người 2 deploy Render/Supabase; Người 3 deploy Vercel.

## Hợp đồng giao tiếp bắt buộc

- Browser không publish ROS message.
- ROS package không nằm trong uv workspace.
- ROS2/Gazebo dùng namespace theo robot, ví dụ `/amr_01` và `/amr_02`.
- Backend và frontend chỉ dùng `RobotTelemetry`, `Task`, `FactoryMetrics` và event contract trong `twin-core`.
- Edge chỉ mở outbound TLS tới Render.
- Không commit secret, database URL hoặc ROS credentials.

## Phân chia môi trường deploy

| Thành phần | Nơi chạy | Vai trò |
|---|---|---|
| Next.js/Three.js | Vercel | Frontend và static/SSR UI |
| FastAPI/WebSocket | Render paid Web Service | REST, auth guard, realtime fan-out, command gateway |
| PostgreSQL/Auth | Supabase | profiles, scenarios, layouts, KPI, approvals |
| Gazebo/ROS2/Nav2 | Ubuntu 24.04 edge hoặc robotics VM | mô phỏng, navigation, fleet/task manager |

`pg_partman` không dùng trong MVP. Chỉ xem xét sau khi có raw telemetry retention
thực tế và benchmark chứng minh PostgreSQL index/retention job không đủ.

## Definition of Done

- Hai AMR chạy trong Gazebo và xuất hiện đúng trên giao diện 3D.
- Task/command từ backend tới ROS2 có acknowledgement.
- Telemetry ROS2 đi qua bridge, backend và WebSocket bằng cùng contract.
- Layout candidate làm thay đổi kết quả SimPy và hiển thị trong comparison.
- Alert abnormal và latency/FPS benchmark có bằng chứng.
- Designer không approve/apply; Monitor không run scenario.
- Vercel, Render, Supabase và edge runbook được kiểm tra bằng deployment smoke test.
