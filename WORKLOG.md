# Worklog — Team Super Extraordinary X

> Dự án P-078 — EV Factory Digital Twin  
> Giai đoạn: **29/07/2026–01/09/2026**  
> Thành viên: **Nguyễn Huy Hưng (Hưng)**, **Nguyễn Xuân Huy (Huy)**, **Nguyễn Tiến Đạt (Đạt)**, **Nguyễn Thị Khánh Ly (Ly)**

Thời gian là số giờ tập trung ước tính, gồm phát triển, họp, kiểm thử và tài liệu. **Hưng và Huy là hai thành viên thực hiện phần lớn khối lượng kỹ thuật; Đạt và Ly tham gia hỗ trợ ở một số mốc kiểm thử, rà yêu cầu và tổng hợp tài liệu.**

## Tuần 1 — Khảo sát và dựng nền (29/07–04/08)

| Ngày | Phân công và kết quả | Status | Time |
|---|---|---|---:|
| 29/07 | **Hưng:** phân tích đề bài/phạm vi Final Assembly. **Huy:** khảo sát UI Digital Twin. **Đạt:** tổng hợp rubric. **Output:** chốt bài toán vận chuyển battery pack bằng AMR. | ✅ Done | 5.5h |
| 30/07 | **Hưng:** phác thảo ROS–cloud architecture. **Huy:** flow Designer/Monitor. **Ly:** ghi biên bản họp và tổng hợp tài liệu tham khảo. **Output:** sơ đồ vertical slice và hai vai trò. | ✅ Done | 6.5h |
| 31/07 | **Hưng:** dựng Python workspace/monorepo. **Huy:** scaffold Next.js. **Output:** khung apps, packages, services, evaluation. | ✅ Done | 6h |
| 01/08 | **Hưng:** domain robot/task/station/route. **Huy:** prototype dashboard. **Output:** domain model và mock data đầu tiên. | ✅ Done | 6h |
| 02/08 | **Hưng:** khảo sát ROS 2/Gazebo. **Huy:** thử camera/layers. **Output:** chốt stack, đơn vị và UTC timestamp. | ✅ Done | 5.5h |
| 03/08 | **Hưng:** REST/WebSocket contract. **Huy:** frontend store theo robot_id. **Output:** contract FE–BE tối thiểu. | ✅ Done | 6h |
| 04/08 | **Hưng:** Ruff/mypy/pytest/CI. **Huy:** ESLint/Vitest/build. **Đạt:** backlog P0/P1. **Output:** quality gates và sprint plan. | ✅ Done | 6.5h |

**Tổng kết tuần:** Khóa phạm vi một vertical slice, contract và nền phát triển song song.

## Tuần 2 — Mock realtime và SimPy (05/08–11/08)

| Ngày | Phân công và kết quả | Status | Time |
|---|---|---|---:|
| 05/08 | **Hưng:** twin-core routing/KPI. **Huy:** factory scene từ fixture. **Output:** domain core và scene độc lập. | ✅ Done | 7h |
| 06/08 | **Hưng:** FastAPI/settings/CORS. **Huy:** API client mock/API. **Output:** backend skeleton. | ✅ Done | 6h |
| 07/08 | **Hưng:** FactoryState/mock engine. **Huy:** robot detail. **Output:** lifecycle deterministic. | ✅ Done | 7.5h |
| 08/08 | **Hưng:** factory/robots/tasks/metrics API. **Huy:** REST store. **Output:** dashboard dùng backend data. | ✅ Done | 7h |
| 09/08 | **Hưng:** WebSocket broadcast. **Huy:** realtime/reconnect. **Output:** mock → FastAPI → WebSocket → UI. | ✅ Done | 8h |
| 10/08 | **Hưng:** SimPy runner. **Huy:** scenario form/KPI comparison. **Ly:** hỗ trợ chuẩn bị dữ liệu scenario mẫu. **Output:** deterministic what-if simulation. | ✅ Done | 9.5h |
| 11/08 | **Hưng:** logging/lifespan/strict mypy. **Huy:** component/API alignment. **Đạt:** full checks. **Output:** backend foundation đạt gates. | ✅ Done | 11h |

**Tổng kết tuần:** Hoàn thành mock realtime và baseline simulation; frontend chuyển mock/API theo cùng contract.

## Tuần 3 — Human-in-the-loop và ROS (12/08–18/08)

| Ngày | Phân công và kết quả | Status | Time |
|---|---|---|---:|
| 12/08 | **Hưng:** battery/charging/alerts. **Huy:** alert panel/KPI chart. **Output:** monitoring cơ bản. | ✅ Done | 8h |
| 13/08 | **Hưng:** scenario API/comparison. **Huy:** nối form. **Output:** what-if end-to-end. | ✅ Done | 8h |
| 14/08 | **Hưng:** approve/reject/apply state machine. **Huy:** role UI. **Output:** apply trước approve trả 409. | ✅ Done | 8h |
| 15/08 | **Hưng:** downsample history. **Huy:** Operations Trend. **Output:** trend 5 giây/5 phút, KPI realtime. | ✅ Done | 6.5h |
| 16/08 | **Hưng:** cloud/edge boundary. **Huy:** responsive/loading/error. **Ly:** rà nội dung tài liệu và checklist demo. **Output:** ROS là acceptance path. | ✅ Done | 7.5h |
| 17/08 | **Hưng:** ROS workspace/URDF. **Huy:** pose adapter. **Output:** AMR spawn trong Gazebo. | ✅ Done | 8.5h |
| 18/08 | **Hưng:** telemetry bridge. **Huy:** realtime pose. **Output:** Gazebo → ROS → backend → 3D. | ✅ Done | 9.5h |

**Tổng kết tuần:** Workflow có guard phía server và AMR đầu tiên truyền telemetry xuyên suốt đến scene 3D.

## Tuần 4 — Multi-AMR, layout và GCP (19/08–25/08)

| Ngày | Phân công và kết quả | Status | Time |
|---|---|---|---:|
| 19/08 | **Hưng:** multi-AMR config/namespace. **Huy:** robot selector. **Output:** fleet nhiều robot. | ✅ Done | 9.5h |
| 20/08 | **Hưng:** fleet/task manager/navigation. **Huy:** route/payload UI. **Output:** ROS task lifecycle. | ✅ Done | 9.5h |
| 21/08 | **Hưng:** immutable layout versions. **Huy:** layout editor. **Output:** scenario truy vết đúng layout. | ✅ Done | 9.5h |
| 22/08 | **Hưng:** bridge/alerts/deploy container. **Huy:** 3D cockpit/2D map. **Output:** advanced vertical slice. | ✅ Done | 14h |
| 23/08 | **Hưng:** Render/env fixes. **Huy:** frontend integration. **Output:** merge ổn định. | ✅ Done | 8h |
| 24/08 | **Hưng:** commands/alerts/GCP backend. **Huy:** layout–simulation–runtime routes. **Output:** full planning flow. | ✅ Done | 15h |
| 25/08 | **Hưng:** Cloud Run/SQL, ledger, CI/CD, edge. **Huy:** demo login/CI. **Ly:** hỗ trợ tổng hợp hướng dẫn triển khai. **Output:** deploy và cost runbooks. | ✅ Done | 15h |

**Tổng kết tuần:** Multi-AMR, layout versioning và command lifecycle hoàn thành; hosted stack chuyển sang GCP-native.

## Tuần 5 — Acceptance và bàn giao (26/08–01/09)

| Ngày | Phân công và kết quả | Status | Time |
|---|---|---|---:|
| 26/08 | **Hưng:** contract/blockers. **Huy:** hosted UI test. **Đạt:** runtime evidence/history/apply hardening. **Output:** readiness B1–B4. | ✅ Done | 13h |
| 27/08 | **Hưng:** P0 triage. **Huy:** hoàn thành 6/7 frontend P0. **Đạt:** verification guide. **Output:** acceptance checklist. | ✅ Done | 10.5h |
| 28/08 | **Hưng:** revision contracts. **Huy:** comparison/zone/timeline/revision UI. **Output:** Monitor yêu cầu sửa, Designer tạo revision. | ✅ Done | 13h |
| 29/08 | **Hưng:** command/alert edge cases. **Huy:** UX/accessibility audit. **Ly:** ghi nhận phản hồi UX trong buổi chạy thử. **Output:** kế hoạch 10 UX checkpoints. | ✅ Done | 9h |
| 30/08 | **Hưng:** reconnect/pause behavior. **Huy:** toast/offline/progress/dialog/tooltips/breadcrumb/freshness. **Output:** UX hoàn thiện. | ✅ Done | 12h |
| 31/08 | **Hưng:** task/apply FE–BE–ROS, collision, benchmark, edge SHA. **Huy:** merge regression. **Output:** runtime end-to-end. | ✅ Done | 13.5h |
| 01/09 | **Hưng:** coordinate frame/runtime parameters/merge. **Huy:** landing page/test format. **Đạt:** final smoke/docs. **Ly:** hỗ trợ tổng hợp tài liệu bàn giao. **Output:** bản bàn giao 01/09. | ✅ Done | 13h |

**Tổng kết tuần:** Hoàn thành revision workflow, UX offline, task/apply xuyên FE–BE–ROS, benchmark và smoke tests.

## Tổng kết giai đoạn

- Gazebo/ROS 2 → telemetry bridge → FastAPI → WebSocket → Next.js/Three.js.
- Monitoring 2D/3D, KPI, alerts, history và connection/freshness state.
- Layout versioning, SimPy what-if và approve–reject–revision–apply.
- PostgreSQL/Cloud SQL, Cloud Run, CI/CD và edge deploy có kiểm tra SHA.
- Unit, integration, frontend, hosted E2E, WebGL, ROS/Gazebo smoke và runtime benchmark.

> Các mốc cuối tháng 8 bám lịch sử Git/tài liệu repository. Các ngày đầu ghi nhận khảo sát, thiết kế và dựng nền trước giai đoạn commit dày.
