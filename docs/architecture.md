# System Architecture

## High-level Architecture

```mermaid
flowchart LR

    GZ[Gazebo]
    ROS[ROS 2]
    BRIDGE[Telemetry Bridge]

    API[FastAPI]
    SIM[Simulation Engine]
    DB[(PostgreSQL / TimescaleDB)]

    WEB[Next.js]
    TWIN[Three.js Digital Twin]

    GZ --> ROS
    ROS --> BRIDGE
    BRIDGE --> API

    SIM --> API
    API --> DB

    API -->|REST / WebSocket| WEB
    WEB --> TWIN
```

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

Đây mới là bản architecture **v0**. Sau này mỗi quyết định lớn cập nhật ADR.