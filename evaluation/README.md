# Mô phỏng và đánh giá hệ thống

## Mục đích

Evaluation của MVP bao phủ cả luồng vận hành trực tiếp ROS 2/Gazebo và luồng phân tích what-if bằng SimPy. Module SimPy cung cấp benchmark mô phỏng sự kiện rời rạc cho các KPI logistics nhà máy xe điện như throughput, cycle time, waiting time, backlog và completion rate. Công cụ này dùng để so sánh nhanh nhiều scenario khi thay đổi số robot, thời gian di chuyển hoặc áp lực nhu cầu.

SimPy không thay thế Gazebo hoặc ROS 2. Luồng vật lý chính là:

```text
Gazebo → ROS 2 → fleet/task manager → telemetry bridge → FastAPI
→ WebSocket → Three.js
```

SimPy là lớp what-if và so sánh layout nhẹ; Gazebo/ROS 2 vẫn là nguồn mô phỏng trực tiếp và telemetry chính.

## Cách định vị evaluation với ban tổ chức

Dự án này **không sử dụng LLM, chatbot, mô hình phân loại, mô hình dự báo hoặc thành phần AI được huấn luyện**. Vì vậy, các chỉ số dành cho mô hình như accuracy, precision/recall, hallucination rate, answer relevance hoặc LLM judge không áp dụng. Gắn các chỉ số này vào dự án sẽ không đánh giá đúng hệ thống thực tế.

Đối tượng được đánh giá là một Digital Twin kỹ thuật. Nguyên tắc vẫn giống evaluation cho AI: xác định input đại diện, hành vi mong đợi, output đo được, quy trình có thể lặp lại và bằng chứng được lưu giữ. Điểm khác biệt là các metric tập trung vào chất lượng mô phỏng, hiệu năng runtime, tính đúng của workflow và khả năng sử dụng trong vận hành thay vì dự đoán của mô hình.

Câu hỏi evaluation dành cho ban tổ chức là:

> Digital Twin có biểu diễn đúng quy trình logistics đã chọn, truyền trạng thái trực tiếp trong giới hạn hiệu năng đo được, so sánh các cấu hình một cách nhất quán và ngăn cấu hình chưa được phê duyệt đi vào runtime hay không?

## Khung đánh giá và bằng chứng hiện tại

| Khía cạnh | Phương pháp và chỉ số | Bằng chứng hiện tại | Trạng thái |
|---|---|---|---|
| Tính đúng chức năng | Unit, API, integration, frontend và ROS contract tests; state transition và mã lỗi mong đợi | Test suite trong từng workspace package | Đã triển khai |
| Hiệu quả scenario | Input baseline/candidate có kiểm soát; throughput, cycle time, waiting time, completion rate và backlog | SimPy batch/benchmark và bản ghi EV-05 | Đã triển khai |
| An toàn workflow | Tách quyền Designer/Monitor; thứ tự SIMULATED → APPROVED → APPLIED; từ chối transition sai | Automated tests và ảnh EV-06 | Đã triển khai |
| Khả năng sử dụng end-to-end | Bảy luồng thủ công về monitoring, alerts, analytics, review và apply | Báo cáo manual evaluation và 11 ảnh | 7/7 luồng đã ghi nhận đều PASS |
| Hiệu năng telemetry | Latency source-to-backend p50/p95/max, update rate từng robot và thời lượng quan sát | Bộ phân tích trong `ev_evaluation.runtime` | Đã có công cụ; còn thiếu báo cáo ROS được lưu trong Git |
| Quan sát collision | Số lần bắt đầu collision và events/giờ từ pose robot | Bộ phân tích footprint bảo thủ | Đã có công cụ; không phải chứng nhận an toàn vật lý |
| Hiệu năng hiển thị | FPS trung bình, p95 frame time và tỷ lệ frame chậm hơn 33,3 ms | Lệnh browser render benchmark | Đã có công cụ; còn thiếu báo cáo đại diện được lưu |
| Acceptance ROS/Gazebo | Từ hai AMR, task dispatch, telemetry bridge, alert và apply acknowledgement | Edge runbook và ROS smoke tests | Còn thiếu bằng chứng full networked acceptance |

Không được diễn giải quá mức bằng chứng hiện tại. Bộ evaluation bảy ca trên trình duyệt sử dụng local API/MVP và chứng minh user workflow, chưa chứng minh toàn bộ đường truyền mạng ROS/Gazebo. Các báo cáo runtime/render JSON sinh tự động đang bị Git ignore; khi nộp bài cần lưu một bộ kết quả đại diện hoặc đính kèm riêng.

## Bộ bằng chứng nên nộp

1. **Scenario benchmark:** baseline và ít nhất hai candidate có input cùng bảng KPI.
2. **Hiệu năng hệ thống:** một lần chạy ROS/Gazebo đại diện với latency p50/p95, update rate, thời lượng và collision events.
3. **Hiệu năng hiển thị:** FPS trung bình, p95 frame time, thông tin trình duyệt và máy demo.
4. **Functional acceptance:** tổng hợp automated tests cùng bảy manual flows và ảnh đã có.
5. **Kiểm tra workflow an toàn:** Designer không được approve/apply, Apply trước approval thất bại và Apply thành công được ROS xác nhận.
6. **Hạn chế:** thời gian SimPy deterministic, physics Gazebo đơn giản, waypoint navigation chưa phải Nav2 production và chưa thử với robot thật.

Đây là system evaluation hợp lệ vì mỗi tuyên bố đều ánh xạ tới một yêu cầu hệ thống đo được. Tên phù hợp là **Đánh giá hệ thống Digital Twin**, không phải **Đánh giá mô hình AI**.

## Yêu cầu môi trường

- Python 3.12
- uv

## Cài đặt

```powershell
uv sync --all-packages --dev
```

Simulation SimPy độc lập không yêu cầu OpenAI API key hoặc kết nối database.

## Chạy một scenario

```powershell
uv run --package ev-factory-simulation python -m ev_sim.runner --scenario services/simulation/scenarios/baseline.json
```

Có thể thay đường dẫn bằng scenario JSON khác trong `services/simulation/scenarios`.

## Chạy batch evaluation

```powershell
.\scripts\evaluate.ps1
```

Script chạy simulation batch trước, sau đó xếp hạng kết quả.

## Định nghĩa KPI

- **Throughput:** số task hoàn thành / số giờ mô phỏng.
- **Cycle Time:** `completed_at - created_at`.
- **Waiting Time:** `started_at - created_at`.
- **Backlog:** tổng số task - số task hoàn thành.
- **Completion Rate:** số task hoàn thành / tổng số task.

## Các scenario chuẩn

- `baseline`: 3 robot, route bình thường và demand profile chuẩn.
- `more_robots`: 6 robot, giữ nguyên route và demand của baseline.
- `congestion`: 3 robot, giữ demand nhưng tăng travel time để mô phỏng route/layout bị tắc nghẽn.

## Logic xếp hạng

Scenario được xếp theo thứ tự:

1. Throughput cao hơn.
2. Cycle time thấp hơn.
3. Waiting time thấp hơn.

Thứ tự này ưu tiên phương án hoàn thành nhiều task hơn trong cùng simulation horizon; cycle time và waiting time là tiêu chí phân hạng tiếp theo.

## File kết quả

- `evaluation/datasets/simulation_results.csv`
- `evaluation/datasets/simulation_results.json`
- `evaluation/reports/benchmark_summary.csv`
- `evaluation/reports/runtime_performance.json`
- `evaluation/reports/render_performance.json`

## Đo hiệu năng runtime

Xuất telemetry đã được backend chấp nhận từ PostgreSQL sau một lần chạy ROS/Gazebo đại diện:

```bash
docker exec ev-twin-postgres psql -U postgres -d postgres -c "\\copy (
select robot_id, source_timestamp, ingested_at, pose, ordering_status
from public.robot_telemetry_history
where ordering_status='ACCEPTED'
order by source_timestamp
) to stdout with csv header" > evaluation/datasets/runtime_telemetry.csv
```

Tính latency source-to-backend, update rate trung bình, số collision và collision events trên mỗi giờ quan sát:

```bash
make runtime-benchmark
```

Đo frame rate trên scene Three.js thực khi frontend local đang chạy:

```bash
make render-benchmark
```

Báo cáo render gồm FPS trung bình, p95 frame time và tỷ lệ frame chậm hơn 33,3 ms. JSON sinh tự động mặc định bị Git ignore.

## Bằng chứng evaluation thủ công

Báo cáo các output quan sát thực tế và ảnh theo timestamp nằm tại [`reports/manual_eval_evidence.md`](reports/manual_eval_evidence.md). Báo cáo có bảy test case về realtime monitoring, scenario benchmark, Monitor review, apply và persisted workflow state.

## Chạy test

```powershell
uv run pytest
```

## Acceptance ROS 2 MVP

Evaluation chưa hoàn chỉnh nếu chưa chứng minh:

- Ít nhất hai AMR chạy trong Gazebo.
- FastAPI nhận telemetry và render robot trong cùng scene 3D như mock data.
- Task/command từ backend tới ROS 2 fleet/task manager.
- Một điều kiện bất thường tạo alert nhìn thấy được.
- Một layout candidate làm thay đổi travel time, congestion hoặc throughput.
- Designer/Monitor phải phê duyệt trước khi apply candidate.
- Đã đo ROS-to-backend latency, quan sát WebSocket trong browser DevTools và đo FPS tự động; database và browser dùng đồng hồ máy chủ đã đồng bộ.

Chạy và ghi lại luồng hosted theo [`docs/runbooks/mvp-edge-acceptance.md`](../docs/runbooks/mvp-edge-acceptance.md). CI backend/database, frontend, ROS và container là gate cần thiết nhưng không thay thế lần chạy acceptance qua Cloud Run, Cloud SQL và GCE edge.

## Hạn chế

- Không mô phỏng đầy đủ động lực học vật lý của robot.
- Chưa có fleet optimization và robot dynamics ở mức production.
- Travel time và loading time là deterministic.
- SimPy chỉ dùng cho KPI/layout benchmark nhanh.
- Incident replay UI đầy đủ và retention vượt policy 30/90 ngày nằm ngoài MVP.
