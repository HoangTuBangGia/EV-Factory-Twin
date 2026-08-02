# Factory Twin — UI Flow

## Vai trò

- **Fleet Operator:** giám sát robot, cảnh báo và KPI.
- **Simulation Engineer:** tạo/chạy kịch bản và gửi duyệt.
- **Reviewer:** xem bằng chứng, phê duyệt hoặc từ chối.
- **Deployment Operator:** xác nhận cửa sổ triển khai và theo dõi kết quả.

Một người có thể mang nhiều vai trò ở bản demo, nhưng quyền vẫn được thể hiện tách biệt trên UI.

## Luồng tổng thể

```mermaid
flowchart TD
    A[Đăng nhập] --> B[Chọn site / zone]
    B --> C[Live Operations Dashboard]
    C --> D[Quan sát AGV, KPI, alerts]
    D --> E{Hành động}

    E -->|Mở cảnh báo| F[Alert Detail]
    F --> G[Focus camera vào vị trí]
    G --> C

    E -->|Bật WOW layer| H[Bottleneck / Drift overlay]
    H --> C

    E -->|Tạo kịch bản| I[Scenario Workbench]
    I --> J[Chỉnh fleet, layout, rules]
    J --> K[Run Simulation]
    K --> L{Run thành công?}
    L -->|Không| M[Sửa cấu hình và chạy lại]
    M --> J
    L -->|Có| N[Benchmark & Risk Report]
    N --> O{Đạt guardrails?}
    O -->|Không| M
    O -->|Có| P[Submit for Review]
    P --> Q[Review Queue]
    Q --> R{Quyết định của người duyệt}
    R -->|Reject / Request changes| M
    R -->|Approve| S[Deployment Confirmation]
    S --> T[Nhập ghi chú + xác nhận site/version]
    T --> U[Queue Deployment]
    U --> V[Backend Deployment Orchestrator]
    V -. adapter boundary .-> W[ROS2 / Robot System]
    V --> X[Audit Log & Deployment Status]
    X --> C
```

## State machine của kịch bản

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Simulating: Run simulation
    Simulating --> Failed: Error / guardrail fail
    Failed --> Draft: Revise
    Simulating --> Evaluated: Run completed
    Evaluated --> Draft: Revise
    Evaluated --> InReview: Submit
    InReview --> ChangesRequested: Reject / request changes
    ChangesRequested --> Draft: Revise
    InReview --> Approved: Human approval
    Approved --> DeploymentQueued: Confirm deployment
    DeploymentQueued --> Deployed: Adapter acknowledges
    DeploymentQueued --> DeploymentFailed: Adapter rejects/fails
    Deployed --> [*]
    DeploymentFailed --> [*]
```

## Quy tắc chuyển trạng thái

| Từ | Hành động | Điều kiện bắt buộc | Sang |
|---|---|---|---|
| Draft | Run simulation | Cấu hình hợp lệ | Simulating |
| Evaluated | Submit | Có run ID, baseline, KPI và risk report | InReview |
| InReview | Approve | Có quyền reviewer và ghi chú | Approved |
| Approved | Queue deployment | Xác nhận site, scenario version và deployment window | DeploymentQueued |
| DeploymentQueued | Execute | Backend kiểm tra approval token còn hiệu lực | Deployed/DeploymentFailed |

## Luồng cảnh báo

```mermaid
flowchart LR
    A[Telemetry event] --> B[Alert xuất hiện ở panel]
    B --> C[User chọn alert]
    C --> D[Camera focus + highlight AGV/zone]
    D --> E{User action}
    E -->|Acknowledge| F[Ghi nhận đã xem]
    E -->|Create scenario| G[Tạo draft với context của alert]
    E -->|Escalate| H[Chuyển người phụ trách]
```
