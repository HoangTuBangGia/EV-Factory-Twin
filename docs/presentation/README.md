# Pitch Deck & Demo Materials

## Files

- `pitch_deck.pptx` — Slide thuyết trình Demo Day
- `video_demo.mp4` — Video demo sản phẩm (tối đa 5 phút)

## Pitch Deck Structure (10 slides)

1. **Title** — Tên dự án + Team
2. **Problem** — Vấn đề là gì? Có bao nhiêu người gặp?
3. **Solution** — Giải pháp AI của bạn
4. **Demo** — Screenshot/Video ngắn
5. **Architecture** — System diagram đơn giản
6. **Tech Stack** — Technologies used
7. **Traction** — Metrics, users, feedback
8. **Market** — Quy mô thị trường
9. **Team** — Ai làm gì
10. **Ask** — Bạn cần gì tiếp theo?

## Video Demo Checklist

- [ ] Giới thiệu problem (< 30 giây)
- [ ] Demo live feature chính (2-3 phút)
- [ ] Hiển thị kết quả benchmark và bước phê duyệt (1 phút)
- [ ] Tóm tắt impact (< 30 giây)

## Slide kiến trúc hiện tại — MVP

```mermaid
flowchart LR
    AUTH[Supabase Auth]
    FE[Next.js UI<br/>Login + role-aware 2D dashboard]
    API[FastAPI<br/>JWT/RBAC + REST + authenticated WS]
    MOCK[MockFactory<br/>Realtime telemetry]
    SIM[SimPy<br/>Offline KPI benchmark]
    DB[(PostgreSQL<br/>profiles + scenarios + audit)]

    AUTH -->|Session| FE
    FE -->|Designer run / Monitor review-apply| API
    API --> SIM
    API --> MOCK
    MOCK -->|Telemetry 10 Hz| API
    API -->|WebSocket| FE
    API <--> DB
```

Thông điệp trình bày:

- MockFactory phục vụ monitoring realtime.
- SimPy phục vụ so sánh nhanh baseline/candidate.
- Server chặn sai role và chặn Apply nếu scenario chưa được Approve.
- Scenario/actor/audit lưu PostgreSQL; state robot/task đang chạy vẫn ở RAM.
- Factory view hiện là 2D; 3D/ROS2/Gazebo chưa hoàn thành.

## Slide kiến trúc mục tiêu — sau MVP

```mermaid
flowchart LR
    GZ[Gazebo / Isaac Sim]
    ROS[ROS2 + Nav2]
    BRIDGE[Telemetry & Command Bridge]
    API[FastAPI]
    DB[(Time-series DB + Audit log)]
    WEB[Next.js + Three.js 3D]
    REVIEW[Designer / Monitor]

    GZ <--> ROS
    ROS <--> BRIDGE
    BRIDGE <--> API
    API <--> DB
    API <-->|REST + WebSocket| WEB
    REVIEW --> WEB
```

Không trình bày kiến trúc mục tiêu như phần đã hoàn thành. Nêu rõ bước tiếp theo là
thay nguồn telemetry MockFactory bằng ROS2 bridge mà không đổi contract frontend.

## Luồng demo 5 phút

1. Overview: trạng thái `LIVE`, robot di chuyển và KPI realtime.
2. Robot detail: pose, pin, task và payload.
3. Scenario: chạy candidate và so sánh với baseline.
4. Chứng minh Designer không có quyền Approve/Apply và Monitor không có quyền Run.
5. Monitor bấm Apply trước Approve để giải thích server-side state guard.
6. Monitor Approve rồi Apply; quay lại Factory và quan sát số robot/config đã reset.
7. Admin xem actor/action/time trong audit log; kết thúc bằng roadmap 3D/ROS2/Gazebo.
