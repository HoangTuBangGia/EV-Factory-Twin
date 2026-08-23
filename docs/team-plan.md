# Team Agreement: ROS2 Digital Twin MVP

## Mục tiêu chung

Xây dựng một vertical slice bám sát `TOPIC.md`:

```text
Layout → SimPy/Gazebo → ROS2 telemetry → FastAPI → WebSocket → 3D factory view
                                      ↓
                              KPI / alerts / latency
                                      ↓
                            approve → apply command
```

Team có hai người:

- **Backend/ROS2:** database, FastAPI, SimPy, ROS2/Gazebo và deployment backend.
- **Frontend:** Next.js, Three.js, layout editor, KPI UI và deployment frontend.

Không tạo một abstraction mới chỉ để kết nối hai phần. Contract trong tài liệu/API
và schema dùng chung là ranh giới bắt buộc.

## Định hướng giao diện

Tham chiếu: [Commercial Digital Twin - Automotive production plant](https://www.youtube.com/watch?v=RAFKl6snHAg).

MVP lấy **3D factory scene làm trung tâm**, với panel thông tin vận hành gọn ở
xung quanh. Không sao chép video hoặc xây mô hình CAD chi tiết; chỉ mô phỏng một
khu vực Battery Buffer → AMR → Marriage Station.

### Factory screen

- 3D scene chiếm vùng chính.
- Camera orbit/pan/zoom và camera reset.
- AMR hiển thị theo đúng tọa độ Gazebo.
- Màu robot theo status.
- Click robot mở detail: battery, task, payload, destination, last update.
- Station, route, no-go zone và congestion zone là các lớp bật/tắt.
- Panel KPI hiển thị throughput, cycle time, waiting, congestion.
- Connection state hiển thị `LIVE`, `DEGRADED` hoặc `OFFLINE`.
- Không dùng hero/landing page; mở ứng dụng là vào factory monitor.

### Scenario/layout screen

- Màn hình riêng cho Designer.
- Layout editor tối giản bằng form hoặc view 2D nhẹ.
- Chỉnh vị trí station, route waypoints, số robot và demand.
- Chạy baseline/candidate.
- Hiển thị bảng so sánh KPI.
- Monitor approve/reject rồi mới apply.

### Giới hạn hình ảnh MVP

- Không xây toàn bộ nhà máy, CAD/BIM hoặc vật liệu photorealistic.
- Không tạo dashboard nhiều card chồng nhau quanh scene.
- Không làm minimap, heatmap 3D và replay nếu chưa cần cho acceptance demo.
- Ưu tiên scene rõ, nhẹ và ổn định trên desktop/mobile.

## Phân công Backend/ROS2

Phụ trách:

- `apps/backend`
- `packages/twin-core`
- `services/simulation`
- `ros2_ws`
- `supabase`
- Render và edge runbook

Đầu ra:

- Hai AMR chạy trong Gazebo với namespace riêng.
- Odometry, battery, status và task state được chuẩn hóa.
- Telemetry đi qua bridge → FastAPI → WebSocket.
- Khi chạy ROS, bridge health là authoritative robot registry; Backend không seed
  robot mock và chỉ nhận telemetry sau khi fleet đăng ký thành công.
- Backend command tới edge/fleet manager có acknowledgement.
- Command history hiển thị từng attempt; chỉ Monitor retry command failed/timeout còn budget.
- Layout/version API và scenario gắn với layout.
- SimPy tính throughput, cycle time, waiting và congestion.
- Supabase lưu profiles, layouts, scenarios, runs/KPI, commands, alerts, audit và telemetry cần thiết.
- Alert stale telemetry, command timeout, robot error và congestion.
- Render service chạy được với Supabase hosted.

## Phân công Frontend

Phụ trách:

- `apps/frontend`
- frontend E2E và Vercel configuration

Đầu ra:

- Factory scene 3D là màn hình chính.
- AMR realtime có pose, orientation, velocity, battery và status.
- Robot detail và alert panel.
- Layer controls cho routes, stations, no-go/congestion zones.
- Layout editor tối giản.
- Scenario form và KPI comparison.
- Designer/Monitor UI permissions.
- Connection state và telemetry latency.
- Vercel build và browser smoke flow.

## Contract bắt buộc

### Runtime boundary

```text
Gazebo → ROS2 → Telemetry Bridge → FastAPI → WebSocket → Next.js/Three.js
```

- Browser không truy cập ROS DDS.
- Frontend không query Supabase tables trực tiếp.
- Backend là nguồn quyết định quyền và KPI authoritative.
- Mock và ROS2 phải trả cùng telemetry contract.

### Robot telemetry

```ts
type RobotTelemetry = {
  timestamp: string;
  robot_id: string;
  pose: { x: number; y: number; yaw: number };
  velocity: { linear: number; angular: number };
  battery: number;
  status:
    | "IDLE"
    | "MOVING_TO_PICKUP"
    | "PICKING"
    | "DELIVERING"
    | "DROPPING"
    | "MOVING_TO_CHARGER"
    | "WAITING"
    | "CHARGING"
    | "ERROR"
    | "OFFLINE";
  task_id: string | null;
  payload_id: string | null;
};
```

Quy ước:

- tọa độ là mét;
- vận tốc là m/s và rad/s;
- battery là `0..100`;
- timestamp là UTC ISO 8601;
- backend giữ `snake_case`;
- nullable field vẫn phải xuất hiện với giá trị `null`.

### WebSocket events

```text
robot.telemetry
task.updated
metrics.updated
alert.created
alert.updated
command.updated
factory.reset
```

Frontend cập nhật store theo `robot_id`, không reload toàn bộ scene.

### Layout

Contract layout này đã được Backend và Frontend dùng chung. `docs/api.md` là
nguồn sự thật cho validation và wire format.

```ts
type FactoryLayout = {
  layout_id: string;
  name: string;
  version: number;
  width: number;
  height: number;
  stations: Array<{
    id: string;
    type: "BATTERY_BUFFER" | "MARRIAGE_STATION" | "CHARGING_STATION";
    x: number;
    y: number;
  }>;
  routes: Array<{
    id: string;
    start_station_id: string;
    end_station_id: string;
    waypoints: Array<{ x: number; y: number }>;
  }>;
  no_go_zones: Array<{
    id: string;
    points: Array<{ x: number; y: number }>;
  }>;
  congestion_zones: Array<{
    id: string;
    delay_multiplier: number;
    points: Array<{ x: number; y: number }>;
  }>;
  config: {
    robot_count: number;
    demand_interval_seconds: number;
    robot_speed_mps: number;
    charger_count: number;
  };
};
```

### Scenario

```ts
type ScenarioRunRequest = {
  name: string;
  layout_id: string;
  layout_version: number;
  route_id: string;
  num_robots: number;
  num_tasks: number;
  task_arrival_interval: number;
  robot_speed_mps: number;
  charger_count: number;
  travel_time: number;
  loading_time: number;
  simulation_time: number;
};
```

Frontend không tự tính KPI authoritative. Backend/SimPy trả:

```ts
type ScenarioMetrics = {
  completed_tasks: number;
  unfinished_tasks: number;
  completion_rate: number;
  throughput_per_hour: number;
  average_cycle_time: number;
  average_waiting_time: number;
  fleet_utilization_percent: number;
  starvation_events: number;
  congestion_percent: number;
  travel_distance: number;
  average_delivery_delay: number;
};
```

## Quy trình phối hợp

1. Backend cập nhật contract trong `docs/api.md` và sample JSON trước.
2. Frontend xây component bằng fixture đúng contract.
3. Backend hoàn thành endpoint và test schema.
4. Frontend đổi fixture sang `apiClient`, không đổi component contract.
5. Hai người cùng kiểm tra ROS2 → backend → WebSocket → 3D.
6. Mọi thay đổi field phải được báo trước và cập nhật cả schema/test/docs.

## Các endpoint chính

Đã có:

```text
GET  /api/v1/factory
GET  /api/v1/robots
GET  /api/v1/tasks
GET  /api/v1/metrics
GET  /api/v1/alerts
POST /api/v1/scenarios/run
POST /api/v1/scenarios/{id}/approve
POST /api/v1/scenarios/{id}/reject
POST /api/v1/scenarios/{id}/apply
WS   /ws/factory
```

Layout/version API đã có và được Layout editor sử dụng:

```text
GET  /api/v1/layouts
GET  /api/v1/layouts/{id}
POST /api/v1/layouts
PATCH /api/v1/layouts/{id}
DELETE /api/v1/layouts/{id}
POST /api/v1/layouts/{id}/versions
GET  /api/v1/layouts/{id}/versions/{version}
```

## Definition of Done

- Hai AMR Gazebo xuất hiện đúng trong scene 3D.
- ROS2 telemetry đi qua backend bằng contract chung.
- Designer tạo layout/scenario và xem KPI comparison.
- Monitor approve/reject trước khi apply.
- Backend command có acknowledgement.
- Alert và connection state hiển thị được.
- Supabase, Render, Vercel và edge runbook được smoke test.
- `make check`, frontend tests/build và ROS CI đều xanh.

## Không thuộc MVP

- incident replay UI đầy đủ và telemetry retention ngoài policy;
- CAD/BIM toàn nhà máy;
- AI chatbot, predictive maintenance, MES/ERP;
- AI/ML hoặc continuous optimizer; bounded deterministic search tối đa 64 candidate thuộc MVP.
