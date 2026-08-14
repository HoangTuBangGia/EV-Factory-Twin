# System Architecture

## Current MVP architecture

```mermaid
flowchart LR
    AUTH[Supabase Auth]
    WEB[Next.js<br/>2D dashboard + role UI]
    API[FastAPI<br/>JWT/RBAC + REST/WS]
    MOCK[MockFactory<br/>10 Hz realtime state]
    SIM[SimPy<br/>scenario benchmark]
    DB[(Supabase PostgreSQL<br/>profiles/scenarios/audit/KPI snapshots)]

    AUTH -->|cookie session / access token| WEB
    WEB <-->|Bearer REST + authenticated WebSocket| API
    API --> MOCK
    API --> SIM
    API <--> DB
```

Robot/task/alert/metrics đang chạy nằm trong RAM và reset khi backend restart.
Profile, scenario workflow, audit log và KPI snapshot 10 giây được lưu PostgreSQL
khi `DATABASE_URL` được cấu hình. Raw robot telemetry 10 Hz không được lưu trong MVP.

## Target architecture

```mermaid
flowchart LR
    GZ[Gazebo]
    ROS[ROS 2 / Nav2]
    BRIDGE[Telemetry & Command Bridge]
    API[FastAPI]
    DB[(Operational PostgreSQL)]
    WEB[Next.js + Three.js]

    GZ <--> ROS
    ROS <--> BRIDGE
    BRIDGE <--> API
    API <--> DB
    API <-->|REST / WebSocket| WEB
```

Gazebo, ROS2, telemetry bridge và Three.js thuộc kiến trúc mục tiêu, chưa phải
thành phần đã hoàn thành của MVP hiện tại.

## Runtime Boundaries
- Edge
- ROS 2
- Gazebo
- Nav2
- Fleet Manager
- Telemetry Bridge
- Application / Cloud
- FastAPI
- PostgreSQL / TimescaleDB
- Simulation Engine
- Next.js
- Three.js

Đây là architecture **v1**. Mỗi quyết định lớn tiếp theo phải cập nhật ADR.
