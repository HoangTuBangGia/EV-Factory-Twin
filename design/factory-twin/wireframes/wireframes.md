# Factory Twin — Low-fidelity Wireframes

## WF-01 — Login & Site Selection

```text
+-------------------------------------------------------------+
| FACTORY TWIN                                  [Help] [About] |
+-------------------------------------------------------------+
|                                                             |
|               +-----------------------------+               |
|               | Sign in                     |               |
|               | Email    [_______________]  |               |
|               | Password [_______________]  |               |
|               | [ Sign in ]                 |               |
|               +-----------------------------+               |
|                                                             |
| Site: [VinUni Test Warehouse v]  Zone: [All zones v]        |
+-------------------------------------------------------------+
```

## WF-02 — Live Operations Dashboard

```text
+--------------------------------------------------------------------------------+
| FACTORY TWIN | Site: Warehouse A v | [Search] | LIVE ● | Alerts 3 | User       |
+-------------+----------------------------------------------------+-------------+
| Navigation  |                                                    | Alerts      |
| [Overview]  |                                                    | [Critical]  |
| [Scenarios] |          3D FACTORY CANVAS PLACEHOLDER             | AGV-07 drift|
| [Reviews 2] |                                                    | [Warning]   |
| [Reports]   |       zones / paths / AGVs / heatmap layers        | Zone B jam  |
| [Settings]  |                                                    +-------------+
|             |                                                    | Fleet       |
|             |                                                    | 07  81% Run |
|             |                                                    | 12  64% Idle|
|             | +------------------------------------------------+ +-------------+
|             | | [Play/Pause] [WOW v] [Benchmark] [New Scenario]| | KPIs        |
|             | +------------------------------------------------+ | 120 task/h  |
|             |                                                    | 45s cycle   |
+-------------+----------------------------------------------------+-------------+
```

Tương tác chính:

- Chọn alert → camera focus vào AGV/zone và mở Alert Detail.
- `WOW` → bật/tắt Bottleneck Predictor và Drift Test overlay.
- `Benchmark` → lưu snapshot KPI làm baseline, không thay đổi hệ thống thật.
- `New Scenario` → tạo draft từ site/layout hiện tại.

## WF-03 — Scenario Workbench

```text
+--------------------------------------------------------------------------------+
| ← Dashboard | Scenario: Zone B Optimization | Draft | SIMULATION ● | Save       |
+---------------------------------------+----------------------------------------+
| Configuration                         | Simulation Preview                     |
| Name       [____________________]      |                                        |
| Base layout [Current production v]    |     2D/3D canvas placeholder            |
| Robot count [ - ] 10 [ + ]            |                                        |
| Routing     [Shortest path v]          |     changed paths highlighted          |
| Max speed   [____] m/s                 |                                        |
| Safety gap  [____] m                   |                                        |
| [Edit layout] [Validate]               |                                        |
+---------------------------------------+----------------------------------------+
| Baseline       Candidate       Delta  | Guardrails                              |
| 107 tasks/h    120 tasks/h     +12%   | ✓ collisions = 0                       |
| 48 sec         45 sec          -6%    | ✓ safety gap                           |
| 18% congestion 11%             -7pp   | ! battery reserve near threshold       |
+---------------------------------------+----------------------------------------+
| [Cancel]                  [Run Simulation] [View Risk Report] [Submit for Review]|
+--------------------------------------------------------------------------------+
```

`Submit for Review` bị vô hiệu hóa cho đến khi run thành công và có risk report.

## WF-04 — Review & Human Approval

```text
+--------------------------------------------------------------------------------+
| Review #RV-1042 | Scenario v3 | Submitted by Simulation Engineer | IN REVIEW    |
+---------------------------------------+----------------------------------------+
| Evidence                              | Decision                               |
| Simulation run: SIM-2026-0814         | Reviewer: [Current user]               |
| Baseline snapshot: BL-221             | Notes:                                 |
| Layout diff: [View changes]           | [____________________________________] |
| KPI comparison: [View report]         | [____________________________________] |
| Risk report: 1 warning, 0 critical    |                                        |
| Audit history: [Open]                 | [Request changes] [Approve scenario]   |
+---------------------------------------+----------------------------------------+
| Warning: Approval does not immediately control robots. It unlocks the separate |
| deployment confirmation step.                                                  |
+--------------------------------------------------------------------------------+
```

## WF-05 — Deployment Confirmation

```text
+---------------------------------------------------------------+
| DEPLOY APPROVED SCENARIO                                      |
+---------------------------------------------------------------+
| Target site       Warehouse A                                 |
| Target zone       Zone B                                      |
| Scenario version  Zone B Optimization / v3                    |
| Approval          RV-1042 / approved by reviewer              |
| Window            [2026-__-__ __:__]                          |
| Rollback plan     [Version v2 v]                              |
| Confirmation      Type DEPLOY-ZONE-B: [____________________]   |
| Notes             [________________________________________]   |
|                                                               |
| [Back]                              [Queue Deployment]         |
+---------------------------------------------------------------+
```

Đây là bước duy nhất tạo deployment intent. Prototype không gửi lệnh robot thật.
