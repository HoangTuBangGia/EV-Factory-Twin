# Weekly Journal — Team Super Extraordinary X

> Dự án P-078 — EV Factory Digital Twin | **29/07/2026–01/09/2026**  
> Thành viên: **Nguyễn Huy Hưng, Nguyễn Xuân Huy, Nguyễn Tiến Đạt, Nguyễn Thị Khánh Ly**

**Phân bổ đóng góp:** Hưng và Huy phụ trách chính phần kiến trúc, backend/ROS, frontend và tích hợp. Đạt và Ly tham gia với khối lượng nhỏ hơn, chủ yếu hỗ trợ kiểm thử, rà yêu cầu, ghi nhận phản hồi và hoàn thiện tài liệu.

## Week 1: 29/07–04/08 — Khảo sát và dựng nền

### Mục tiêu và kết quả

- [x] Chốt bài toán, target user, MVP, kiến trúc và contract.
- [x] Chọn ROS 2/Gazebo, FastAPI/WebSocket, Next.js/Three.js và SimPy.
- [x] Dựng monorepo, fixture và quality gates.

### Khó khăn & Giải pháp

| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| Phạm vi Digital Twin quá rộng | Khóa Battery Buffer → AMR → Marriage Station | MVP đủ sâu và khả thi |
| FE/BE dễ chờ nhau | Schema/fixture trước implementation | Phát triển song song |
| ROS và 3D dễ lệch quy ước | Chốt frame, đơn vị, timestamp | Giảm lỗi tích hợp |

### Bài học và kế hoạch

- Vertical slice end-to-end có giá trị hơn nhiều màn hình rời rạc.
- Tuần sau: mock factory, REST/WebSocket, factory scene và SimPy baseline.

## Week 2: 05/08–11/08 — Mock realtime và simulation

### Mục tiêu và kết quả

- [x] Hoàn thành twin-core, FastAPI foundation và FactoryState.
- [x] REST snapshot/WebSocket, reconnect, factory scene và robot detail.
- [x] SimPy deterministic baseline; Ruff, mypy, pytest, ESLint, Vitest và CI.

### Khó khăn & Giải pháp

| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| Fixture khác backend | Adapter mock/API theo một contract | Không viết lại component |
| Engine dễ chạy lúc import | ASGI lifespan | Test/import ổn định |
| uv workspace nhiều package | Chuẩn hóa sync all-packages | Dev/CI tái lập được |

### Bài học và kế hoạch

- Business state tách khỏi route; WebSocket truyền delta theo robot_id.
- Tuần sau: alerts/history, approval workflow và ROS telemetry đầu tiên.

## Week 3: 12/08–18/08 — Human-in-the-loop và ROS

### Mục tiêu và kết quả

- [x] Run/comparison/approve/reject/apply; apply trước approve trả 409.
- [x] Alerts và trend downsample 5 giây trong cửa sổ 5 phút.
- [x] Gazebo → ROS 2 → FastAPI → WebSocket → frontend 3D.

### Khó khăn & Giải pháp

| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| SimPy/runtime khác tham số | Chỉ map phần có nghĩa chung | Không tuyên bố sai khả năng apply |
| Approval có thể bypass UI | Server-side transition guard | Human-in-the-loop thực sự |
| ROS/Three.js khác frame | Pose adapter và quy ước chung | Hiển thị nhất quán |

### Bài học và kế hoạch

- Guard phải ở trust boundary; mock và ROS khác vai trò nhưng chung contract.
- Tuần sau: multi-AMR, layout versions/editor và cloud deployment.

## Week 4: 19/08–25/08 — Multi-AMR, layout và GCP

### Mục tiêu và kết quả

- [x] Multi-AMR, fleet/task manager, navigation và charging.
- [x] 3D cockpit, 2D map, route network và immutable layout versions.
- [x] Commands/history/alerts; GCP auth/PostgreSQL, Cloud SQL, Cloud Run và CI/CD.

### Khó khăn & Giải pháp

| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| Mock và ROS có thể trộn | ROS registry authoritative | Acceptance không lẫn fixture |
| Layout đổi mất truy vết | Lưu layout ID/version bất biến | Benchmark tái lập |
| DB lỗi chặn telemetry | Tách broadcast khỏi persistence phụ | Realtime vẫn chạy |
| Migration schema drift | Ledger kiểm checksum | Deploy an toàn hơn |

### Bài học và kế hoạch

- DDS ở edge; browser chỉ qua HTTP/WebSocket. Deploy cần evidence và cost control.
- Tuần sau: B1–B4, hosted E2E, revision workflow, UX và benchmark.

## Week 5: 26/08–01/09 — Acceptance và bàn giao

### Mục tiêu và kết quả

- [x] Runtime evidence, bounded history, hardened apply và verification guide.
- [x] Live/candidate comparison, zone editor, timeline và revision request.
- [x] Hosted E2E: Monitor yêu cầu sửa → Designer tạo revision → duyệt/apply.
- [x] Offline/reconnect, pause, progress, accessible dialog, tooltips và freshness.
- [x] Task/apply FE–BE–ROS, collision alerts, benchmark, Gazebo/DB smoke và edge SHA.
- [x] Coordinate alignment, runtime parameters, landing page và tài liệu bàn giao.

### Khó khăn & Giải pháp

| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| Offline/stale/paused dễ nhầm | Banner, reconnect, freshness state | Trạng thái rõ ràng |
| Native confirm kém accessibility | Dialog hỗ trợ focus/keyboard | Thao tác an toàn |
| Apply chưa chắc tới ROS | Ack và command timeline | Quan sát đến edge |
| Edge có thể sai commit | Verify SHA trên remote | Evidence đúng phiên bản |
| AMR lệch factory model | Căn coordinate frame | Pose khớp scene |

### Bài học

- Workflow chỉ hoàn chỉnh khi quan sát được success, failure, timeout và retry.
- Acceptance cần automated tests, hosted E2E, ROS/Gazebo smoke và benchmark.

### Hạn chế hiện tại của ROS 2/Gazebo

| Hạn chế | Ảnh hưởng hiện tại | Hướng cải thiện |
|---|---|---|
| Navigation đang dùng waypoint-following và điều khiển `Twist` xác định trước, chưa phải Nav2 production | Robot đi được theo route cấu hình nhưng chưa tự lập kế hoạch lại khi môi trường thay đổi | Tích hợp Nav2 planner/controller, costmap và recovery behavior |
| Chưa có dynamic obstacle avoidance và fleet traffic reservation đầy đủ | Nhiều AMR chỉ được điều phối trong phạm vi bounded; chưa bảo đảm tránh deadlock hoặc va chạm trong tình huống phức tạp | Thêm traffic manager, reservation theo đoạn đường và conflict resolution |
| Gazebo dùng planar `VelocityControl`, chưa mô phỏng wheel-contact physics và dynamic wheel transforms | Chuyển động phù hợp cho demo logic/telemetry nhưng chưa phản ánh chính xác độ trượt, gia tốc, tải và động lực học robot thật | Dùng joint/wheel controller, bridge joint states và hiệu chỉnh tham số vật lý |
| Collision hiện được phát hiện bằng vòng tròn bảo thủ quanh footprint | Hệ thống tạo cảnh báo khi vùng bao chồng lấn, nhưng không đo contact force và không tự tránh va chạm | Kết hợp Gazebo contact sensor với collision avoidance ở navigation layer |
| Chỉ tốc độ robot có thể cập nhật khi runtime đang chạy | Đổi layout/version, route, số robot, charger capacity hoặc demand cadence phải restart simulation và bridge | Xây topology-aware adapter và quy trình reconfigure an toàn |
| ROS 2 Jazzy/Gazebo Harmonic cần Ubuntu 24.04 hoặc edge VM phù hợp; không chạy trực tiếp trên Cloud Run/Vercel | Việc demo/deploy phụ thuộc máy edge, cấu hình DDS và tài nguyên đồ họa/CPU | Đóng gói môi trường edge, tự động hóa provisioning và chuẩn bị video demo dự phòng |
| CI Gazebo chạy headless server-only; một số máy phát triển không có `/opt/ros`, `rclpy` hoặc `colcon` | Static/unit/launch tests không thay thế được kiểm thử trực quan và acceptance full-stack trên môi trường ROS thật | Duy trì một edge runner có ROS/Gazebo để chạy định kỳ và lưu runtime evidence |
| Chưa kiểm chứng với AMR vật lý, cảm biến thật hoặc nhiễu mạng công nghiệp | Kết quả hiện tại chỉ chứng minh simulation MVP, chưa đủ kết luận về production safety/reliability | Hardware-in-the-loop, sensor/noise testing, network fault injection và safety review |

Các hạn chế trên không chặn luồng demo MVP, nhưng cần được nêu rõ: hệ thống hiện chứng minh **tích hợp Digital Twin và workflow vận hành**, chưa phải bộ điều khiển robot production hoặc bằng chứng an toàn cho nhà máy thật.

### Việc tiếp theo

- [ ] Rehearsal đúng môi trường trình bày và quay video dự phòng.
- [ ] Chạy full-stack acceptance trên edge có ROS 2 Jazzy/Gazebo Harmonic và lưu log/benchmark.
- [ ] Thử Nav2 cùng dynamic obstacle avoidance trên một route chuẩn trước khi mở rộng topology.
- [ ] Tắt tài nguyên GCP không cần thiết sau demo.
- [ ] Incident replay, retention dài hạn và MES/ERP để sau MVP.

## Tổng kết

Trong 5 tuần, với Hưng và Huy đảm nhiệm phần lớn công việc phát triển và tích hợp, nhóm đi từ đề bài rộng đến vertical slice khép kín. Ba quyết định chính là FastAPI làm ranh giới authoritative giữa edge/browser, mock và ROS dùng chung telemetry contract, và Monitor phải duyệt trước khi apply.

> Journal tổng hợp từ kiến trúc, dev log, change notes và lịch sử Git; tuần đầu phản ánh khảo sát/thiết kế trước giai đoạn commit dày.
