# EV Factory Digital Twin — Frontend Implementation Guide

> **Project:** EV Factory Digital Twin — AMR-based Battery Intralogistics  
> **Scope:** Frontend only  
> **Current phase:** Unified MOCK/ROS2 Web MVP with authenticated REST and WebSocket contracts
> **Frontend stack:** Next.js + TypeScript + Tailwind CSS + Zustand + Zod + ECharts + Vitest  
> **Visualization:** Data-driven 2D and Three.js / React Three Fiber views

---

## 1. Frontend objective

Frontend is responsible for turning factory state and telemetry received from the backend into a clear, real-time Digital Twin interface.

For the current phase, the frontend does **not** need to know whether telemetry comes from mock data, Gazebo, ROS2, or a real robot.

The frontend depends only on a stable backend contract:

```text
Telemetry Source
    │
    ├── Mock
    ├── ROS2 / Gazebo
    └── Replay
        │
        ▼
      FastAPI
        │
        ├── REST API
        └── WebSocket
              │
              ▼
          FRONTEND
```

The most important frontend requirement is:

> The UI must work unchanged when the backend telemetry source changes from MOCK to ROS in the future.

---

## 2. Product context

The system represents the battery intralogistics area of an electric vehicle final-assembly factory.

AMRs transport battery packs from the Battery Buffer to the Battery Marriage Station.

```text
Battery Buffer
     │
     │ AMR picks battery pack
     ▼
AMR Transport
     │
     ▼
Battery Marriage Station
     │
     ▼
Battery delivered to vehicle assembly
```

The frontend should help users answer:

- Where are all AMRs right now?
- Which AMR is carrying which battery pack?
- What task is each AMR performing?
- Which robots are idle, charging, waiting, or in error?
- Are any batteries low?
- What is current throughput?
- Are there active alerts?
- Can the user inspect a specific AMR or task?

---

## 3. Frontend responsibilities

Frontend owns:

1. Application shell and navigation.
2. Dashboard presentation.
3. Factory map / Digital Twin visualization.
4. Real-time WebSocket connection.
5. Initial data loading through REST.
6. Client-side state management.
7. Robot fleet visualization.
8. Robot details.
9. Task list and task details.
10. KPI cards and charts.
11. Alerts panel.
12. Loading, empty, offline, and error states.
13. WebSocket reconnect behavior.
14. Basic scenario controls later in the MVP.
15. Frontend tests.
16. Frontend CI checks.

Frontend does **not** own:

- robot task assignment logic;
- battery drain calculation;
- throughput calculation;
- task generation;
- collision detection;
- factory simulation logic;
- robot path planning;
- KPI formulas.

These values come from the backend.

---

## 4. Recommended frontend stack

```text
Next.js
TypeScript
Tailwind CSS
Zustand
Zod
ECharts
Vitest
Testing Library
```

Optional once 2D realtime is stable:

```text
Three.js
@react-three/fiber
@react-three/drei
```

Install:

```bash
cd apps/frontend

npm install \
  zustand \
  zod \
  echarts \
  echarts-for-react

npm install -D \
  vitest \
  @testing-library/react \
  @testing-library/jest-dom \
  jsdom
```

For later 3D:

```bash
npm install \
  three \
  @react-three/fiber \
  @react-three/drei
```

---

## 5. Suggested directory structure

```text
apps/frontend/
├── public/
│   ├── icons/
│   └── models/
│
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── factory/page.tsx
│   │   ├── fleet/page.tsx
│   │   ├── tasks/page.tsx
│   │   ├── analytics/page.tsx
│   │   └── scenarios/page.tsx
│   │
│   ├── components/
│   │   ├── layout/
│   │   ├── dashboard/
│   │   ├── factory/
│   │   ├── fleet/
│   │   ├── tasks/
│   │   ├── alerts/
│   │   └── charts/
│   │
│   ├── features/
│   │   ├── factory/
│   │   ├── fleet/
│   │   ├── tasks/
│   │   ├── telemetry/
│   │   ├── alerts/
│   │   └── scenarios/
│   │
│   ├── hooks/
│   │   ├── use-factory-socket.ts
│   │   └── use-initial-factory-data.ts
│   │
│   ├── lib/
│   │   ├── api-client.ts
│   │   ├── websocket-client.ts
│   │   ├── env.ts
│   │   └── coordinate.ts
│   │
│   ├── stores/
│   │   └── factory-store.ts
│   │
│   ├── schemas/
│   │   ├── robot.ts
│   │   ├── task.ts
│   │   ├── telemetry.ts
│   │   ├── metric.ts
│   │   ├── alert.ts
│   │   └── websocket-event.ts
│   │
│   └── test/
│       └── setup.ts
│
├── .env.example
├── package.json
├── package-lock.json
├── tsconfig.json
└── vitest.config.ts
```

Do not create every file immediately. Add files as features are implemented.

---

## 6. Core data contracts

### 6.1 Robot status

```ts
export type RobotStatus =
  | "IDLE"
  | "MOVING_TO_PICKUP"
  | "PICKING"
  | "DELIVERING"
  | "DROPPING"
  | "WAITING"
  | "CHARGING"
  | "ERROR"
  | "OFFLINE";
```

Do not invent frontend-only status names.

### 6.2 Robot telemetry

Expected payload:

```json
{
  "timestamp": "2026-08-11T04:00:00.125Z",
  "robot_id": "AMR-01",
  "pose": {
    "x": 12.4,
    "y": 7.8,
    "yaw": 1.57
  },
  "velocity": {
    "linear": 1.1,
    "angular": 0.0
  },
  "battery": 82.4,
  "status": "DELIVERING",
  "task_id": "TASK-102",
  "payload_id": "BP-102"
}
```

TypeScript:

```ts
export interface RobotTelemetry {
  timestamp: string;
  robot_id: string;

  pose: {
    x: number;
    y: number;
    yaw: number;
  };

  velocity: {
    linear: number;
    angular: number;
  };

  battery: number;
  status: RobotStatus;
  task_id: string | null;
  payload_id: string | null;
}
```

### 6.3 Robot model

```ts
export interface Robot {
  id: string;
  name: string;
  status: RobotStatus;
  battery: number;

  pose: {
    x: number;
    y: number;
    yaw: number;
  };

  velocity: {
    linear: number;
    angular: number;
  };

  task_id: string | null;
  payload_id: string | null;
  last_seen_at: string;
}
```

---

## 7. Task contract

```ts
export type TaskStatus =
  | "QUEUED"
  | "ASSIGNED"
  | "PICKUP"
  | "IN_PROGRESS"
  | "DELIVERED"
  | "COMPLETED"
  | "FAILED";
```

```ts
export interface Task {
  task_id: string;
  type: "DELIVER_BATTERY";

  payload_id: string;
  pickup: string;
  dropoff: string;

  assigned_robot_id: string | null;
  status: TaskStatus;

  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}
```

---

## 8. Metric contract

```ts
export interface FactoryMetrics {
  completed_tasks: number;
  throughput_per_hour: number;
  average_cycle_time_seconds: number;
  active_tasks: number;
  queued_tasks: number;
  starvation_events: number;
  fleet_utilization_percent: number;
}
```

Frontend should **not calculate these business metrics from telemetry**. Backend owns the formulas.

---

## 9. Alert contract

```ts
export type AlertSeverity = "INFO" | "WARNING" | "CRITICAL";

export interface FactoryAlert {
  id: string;
  severity: AlertSeverity;
  code: string;
  message: string;
  robot_id: string | null;
  task_id: string | null;
  timestamp: string;
}
```

---

## 10. REST API expected by frontend

Base URL in development:

```text
http://localhost:8000
```

Expected endpoints:

```text
GET /health

GET /api/v1/factory
GET /api/v1/robots
GET /api/v1/robots/{robot_id}
GET /api/v1/tasks
GET /api/v1/tasks/{task_id}
GET /api/v1/metrics
GET /api/v1/alerts
```

Optional mock control endpoints:

```text
POST /api/v1/mock/start
POST /api/v1/mock/stop
POST /api/v1/mock/reset
POST /api/v1/mock/speed
```

Centralize HTTP calls in:

```text
src/lib/api-client.ts
```

Do not scatter raw `fetch()` calls throughout components.

---

## 11. WebSocket contract

Development endpoint:

```text
ws://localhost:8000/ws/factory
```

Use one WebSocket for realtime factory events initially.

Robot event:

```json
{
  "type": "robot.telemetry",
  "data": {}
}
```

Task event:

```json
{
  "type": "task.updated",
  "data": {}
}
```

Metrics event:

```json
{
  "type": "metrics.updated",
  "data": {}
}
```

Alert event:

```json
{
  "type": "alert.created",
  "data": {}
}
```

Alert lifecycle update:

```json
{
  "type": "alert.updated",
  "data": { "status": "CLEARED" }
}
```

---

## 12. Validate external data with Zod

Do not trust WebSocket JSON blindly.

```ts
import { z } from "zod";

export const robotStatusSchema = z.enum([
  "IDLE",
  "MOVING_TO_PICKUP",
  "PICKING",
  "DELIVERING",
  "DROPPING",
  "WAITING",
  "CHARGING",
  "ERROR",
  "OFFLINE",
]);

export const robotTelemetrySchema = z.object({
  timestamp: z.string(),
  robot_id: z.string(),

  pose: z.object({
    x: z.number(),
    y: z.number(),
    yaw: z.number(),
  }),

  velocity: z.object({
    linear: z.number(),
    angular: z.number(),
  }),

  battery: z.number().min(0).max(100),
  status: robotStatusSchema,
  task_id: z.string().nullable(),
  payload_id: z.string().nullable(),
});
```

If invalid data arrives:

- log during development;
- ignore the event;
- never crash the dashboard.

---

## 13. Initial-load + realtime architecture

On page load:

```text
GET /robots
GET /tasks
GET /metrics
GET /alerts
```

This creates the initial snapshot.

Then connect:

```text
WS /ws/factory
```

WebSocket provides incremental updates.

```text
REST
 │
 ▼
Initial state
 │
 ▼
Zustand Store
 ▲
 │
WebSocket updates
```

---

## 14. Zustand store design

```ts
interface FactoryStore {
  robots: Record<string, Robot>;
  tasks: Record<string, Task>;
  metrics: FactoryMetrics | null;
  alerts: FactoryAlert[];

  connectionStatus: "CONNECTING" | "LIVE" | "OFFLINE";

  setRobots: (robots: Robot[]) => void;
  updateRobotTelemetry: (telemetry: RobotTelemetry) => void;

  setTasks: (tasks: Task[]) => void;
  updateTask: (task: Task) => void;

  setMetrics: (metrics: FactoryMetrics) => void;
  addAlert: (alert: FactoryAlert) => void;

  setConnectionStatus: (
    status: "CONNECTING" | "LIVE" | "OFFLINE"
  ) => void;
}
```

Prefer `Record<string, Robot>` over arrays for realtime robot updates.

---

## 15. WebSocket behavior

Required flow:

```text
CONNECTING
    │
    ▼
  LIVE
    │
connection lost
    ▼
 OFFLINE
    │
 retry
    ▼
  LIVE
```

Suggested reconnect delays:

```text
1 sec
2 sec
4 sec
8 sec
max 10 sec
```

Do not require browser refresh after backend restart.

Always show textual status such as `LIVE`, `CONNECTING`, or `OFFLINE`; do not rely on color alone.

---

## 16. Required pages

### `/` — Overview Dashboard

Recommended layout:

```text
┌─────────────────────────────────────────────────────────┐
│ EV FACTORY DIGITAL TWIN                     LIVE ●      │
├─────────────────────────────────────────────────────────┤
│ Throughput │ Fleet │ Avg Cycle │ Starvation │ Tasks    │
├───────────────────────────────────┬─────────────────────┤
│                                   │ Fleet               │
│         FACTORY MAP               │ R01 DELIVERING      │
│                                   │ R02 IDLE            │
│                                   │ R03 CHARGING        │
│                                   │ R04 PICKING         │
│                                   │ R05 MOVING          │
├───────────────────────────────────┼─────────────────────┤
│ Throughput / Cycle chart          │ Alerts              │
└───────────────────────────────────┴─────────────────────┘
```

Required:

- KPI cards;
- factory map;
- fleet summary;
- recent alerts;
- connection status.

---

## 17. KPI cards

At minimum:

```text
Throughput
Fleet Online
Average Cycle Time
Starvation Events
Active Tasks
```

Display values cleanly:

```text
61.4 tasks/h
52.8 s
72.1%
```

---

## 18. `/factory` — Factory Digital Twin

Build **2D first, not 3D**.

Recommended implementation: SVG.

```text
┌─────────────────────────────────────────────────────┐
│  BATTERY BUFFER                                     │
│  ┌───────────┐                                      │
│  │ BP racks  │   ● AMR-01 ───────────┐             │
│  └───────────┘                       │             │
│                                      ▼             │
│                            ● AMR-03                 │
│                                      │             │
│                                      ▼             │
│                           MARRIAGE STATION          │
│                                                     │
│ CHARGING                                            │
│ ┌───────────┐                                       │
│ │ ● AMR-05  │                                       │
│ └───────────┘                                       │
└─────────────────────────────────────────────────────┘
```

SVG is preferable for MVP because markers are easy to click, label, inspect, and test.

---

## 19. Coordinate system

Backend coordinates are factory meters, not pixels.

Example:

```text
Factory:
x = 0 → 20 m
y = 0 → 15 m

Screen:
1000 × 750 px
```

Create:

```text
src/lib/coordinate.ts
```

Example:

```ts
export function worldToScreen(
  x: number,
  y: number,
  factoryWidth: number,
  factoryHeight: number,
  screenWidth: number,
  screenHeight: number,
) {
  return {
    x: (x / factoryWidth) * screenWidth,
    y: screenHeight - (y / factoryHeight) * screenHeight,
  };
}
```

Document this convention because ROS integration later must use the same coordinate model.

---

## 20. Robot marker

Each robot marker should show:

```text
AMR-01
82%
●
```

Click robot → select robot → open detail drawer.

Orientation should use `yaw`.

Make motion visually smooth. Do not implement complicated physics interpolation during MVP.

---

## 21. `/fleet` — Fleet page

Columns:

```text
Robot
Status
Battery
Speed
Current Task
Payload
Last Seen
```

Filters:

```text
All
Active
Idle
Charging
Warning
Error
```

---

## 22. Robot detail drawer

Display:

```text
AMR-01

Status
DELIVERING

Battery
82%

Speed
1.1 m/s

Position
X 12.42 m
Y 7.81 m
Yaw 1.57 rad

Current Task
TASK-101

Payload
BP-101
```

Optional later:

- history;
- traveled path;
- ETA;
- battery history.

---

## 23. `/tasks` — Task page

Columns:

```text
Task
Payload
Pickup
Dropoff
Robot
Status
Created
Duration
```

Example:

```text
TASK-101  BP-101  Buffer  Marriage  AMR-01  IN_PROGRESS
TASK-102  BP-102  Buffer  Marriage  AMR-04  PICKUP
TASK-103  BP-103  Buffer  Marriage  —       QUEUED
```

---

## 24. Alerts UI

Use a persistent panel rather than temporary toast only.

Example:

```text
WARNING
AMR-05 battery below 20%
10 seconds ago

WARNING
Task backlog above threshold
38 seconds ago
```

Alert should expose:

- severity;
- message;
- timestamp;
- linked robot/task where possible.

---

## 25. Analytics

Start with:

- throughput trend;
- cycle-time trend;
- fleet utilization;
- completed tasks;
- starvation events.

Use ECharts.

Do not invent historical factory data and present it as real. If backend history does not exist yet, use explicit development fixtures.

---

## 26. Scenario controls — later in MVP

After realtime monitoring works, add:

```text
Robot Count
Task Interval
Robot Speed
Simulation Speed
Battery Drain Mode
```

Example:

```text
Robot count
[-] 5 [+]

Task interval
8 seconds

Robot speed
1.2 m/s

Simulation speed
1x  2x  4x

[Reset]               [Apply]
```

Do not implement a CAD layout editor in the first frontend sprint.

---

## 27. App shell

Recommended navigation:

```text
Overview
Factory
Fleet
Tasks
Analytics
Scenarios
```

Desktop-first layout is appropriate.

---

## 28. Status conventions

Use a consistent semantic representation:

```text
IDLE               neutral
MOVING_TO_PICKUP   active
PICKING            active
DELIVERING         active
DROPPING           active
WAITING            warning
CHARGING           info
ERROR              critical
OFFLINE            muted
```

Always pair color with text/icon.

---

## 29. Loading, empty, and error states

Every REST-powered section needs:

```text
loading
success
empty
error
```

Examples:

```text
No active tasks.
New battery delivery tasks will appear here.
```

```text
Unable to load factory data.

[Retry]
```

If WebSocket is lost but snapshot data exists:

```text
OFFLINE
Showing last known factory state.
```

Do not blank the UI.

---

## 30. Environment variables

Create:

```text
apps/frontend/.env.example
```

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/factory
```

Never hardcode backend URLs in components.

---

## 31. API client

Centralize API access.

Expected functions:

```text
getFactory()
getRobots()
getRobot(id)
getTasks()
getMetrics()
getAlerts()
updateMockConfig()
resetMockFactory()
```

Do not put repeated fetch logic in page components.

---

## 32. Realtime rendering performance

Telemetry may arrive at 10 Hz for five robots.

Guidelines:

- store robots by ID;
- subscribe components only to required state;
- do not store unlimited telemetry history in Zustand;
- avoid app-wide context updates per telemetry event;
- current state and historical state should be separate concerns.

---

## 33. Testing requirements

Use:

```text
Vitest
Testing Library
```

Minimum tests:

### Robot card

Given AMR-01, battery 82, status DELIVERING:

```text
AMR-01 visible
82% visible
DELIVERING visible
```

### Low battery

Battery = 15 → warning indicator visible.

### Metrics

Throughput = 61.4 → correctly formatted.

### Realtime store update

Initial:

```text
AMR-01 x = 1
```

Event:

```text
AMR-01 x = 5
```

Expected:

```text
store AMR-01 x = 5
```

### Invalid WebSocket message

Expected:

```text
app does not crash
store is not corrupted
```

---

## 34. Frontend CI

Add a frontend job to `.github/workflows/ci.yml` once the app exists.

Expected commands:

```text
npm ci
npm run lint
npm run test
npm run build
```

Example:

```yaml
frontend-quality:
  name: Frontend Quality
  runs-on: ubuntu-24.04

  defaults:
    run:
      working-directory: apps/frontend

  steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Setup Node
      uses: actions/setup-node@v4
      with:
        node-version: 22
        cache: npm
        cache-dependency-path: apps/frontend/package-lock.json

    - name: Install dependencies
      run: npm ci

    - name: Lint
      run: npm run lint

    - name: Test
      run: npm run test -- --run

    - name: Build
      run: npm run build
```

---

## 35. Git workflow

Start from current `develop`:

```bash
git switch develop
git pull --ff-only origin develop

git switch -c feat/frontend-foundation
```

Suggested follow-up branches:

```text
feat/frontend-foundation
feat/factory-map
feat/realtime-telemetry
feat/fleet-dashboard
feat/task-dashboard
feat/alerts-ui
feat/analytics-dashboard
feat/scenario-controls
```

Avoid one giant frontend PR.

---

# 36. Frontend implementation roadmap

## FE-0 — Foundation

Goal: Next.js builds locally and in CI.

```text
[ ] Create Next.js app
[ ] TypeScript
[ ] Tailwind
[ ] Setup Vitest
[ ] Setup Testing Library
[ ] Add frontend CI
[ ] Add .env.example
[ ] Create basic app shell
```

Definition of done:

```text
npm run lint   passes
npm run test   passes
npm run build  passes
CI             green
```

---

## FE-1 — Static dashboard

Do not connect backend yet.

Use fixture data for:

```text
5 AMRs
3 tasks
3 alerts
factory metrics
```

Build:

```text
[ ] Sidebar
[ ] Topbar
[ ] Connection badge placeholder
[ ] KPI cards
[ ] Fleet table
[ ] Task table
[ ] Alert list
```

---

## FE-2 — REST integration

Replace initial fixture state with:

```text
[ ] GET robots
[ ] GET tasks
[ ] GET metrics
[ ] GET alerts
[ ] Loading states
[ ] Error states
[ ] Retry behavior
```

Acceptance:

> Refreshing the page shows the current backend factory snapshot.

---

## FE-3 — WebSocket integration

```text
[ ] WebSocket client
[ ] Zod event validation
[ ] robot.telemetry handler
[ ] task.updated handler
[ ] metrics.updated handler
[ ] alert.created handler
[ ] alert.updated handler
[ ] reconnect logic
[ ] LIVE/OFFLINE indicator
```

Acceptance:

> When the mock backend moves AMR-01, AMR-01 updates on the browser without refresh.

---

## FE-4 — 2D factory map

```text
[ ] Factory boundary
[ ] Battery Buffer
[ ] Marriage Station
[ ] Charging Station
[ ] Robot markers
[ ] Coordinate conversion
[ ] Robot orientation
[ ] Robot selection
[ ] Robot detail drawer
```

Acceptance:

> Five AMRs move according to backend `(x, y, yaw)` telemetry.

---

## FE-5 — Operations polish

```text
[ ] Better status badges
[ ] Battery warning
[ ] Alert interactions
[ ] Task filters
[ ] Fleet filters
[ ] Metric formatting
[ ] Empty states
[ ] Error states
[ ] Last-known-state behavior
```

---

## FE-6 — Analytics

```text
[ ] Throughput chart
[ ] Cycle-time chart
[ ] Fleet utilization
[ ] Starvation display
```

---

## FE-7 — Scenario controls

```text
[ ] Robot count
[ ] Task interval
[ ] AMR speed
[ ] Simulation speed
[ ] Reset
[ ] Apply
```

---

# 37. Frontend MVP acceptance criteria

```text
[ ] Next.js builds in CI
[ ] TypeScript build succeeds
[ ] Lint passes
[ ] Tests pass

[ ] Overview page exists
[ ] Factory page exists
[ ] Fleet page exists
[ ] Tasks page exists

[ ] Initial state comes from REST
[ ] WebSocket connects automatically
[ ] WebSocket reconnects after backend restart
[ ] Connection status is visible

[ ] Five AMRs appear on factory map
[ ] AMR positions update realtime
[ ] AMR orientation updates
[ ] Robot state updates
[ ] Battery updates

[ ] Robot detail opens
[ ] Task is visible
[ ] Payload is visible

[ ] KPI cards update
[ ] Alerts appear
[ ] Low-battery state is visible

[ ] Loading state exists
[ ] Empty state exists
[ ] API error state exists
[ ] Offline realtime state exists

[ ] Invalid WebSocket payload does not crash UI
[ ] Frontend does not depend on MOCK/ROS source details
```

---

# 38. Suggested GitHub issues

## FE-001 — Bootstrap frontend

Acceptance:

```text
[ ] apps/frontend exists
[ ] Next.js + TypeScript works
[ ] Tailwind works
[ ] package-lock committed
[ ] npm run lint passes
[ ] npm run build passes
[ ] frontend CI green
```

## FE-002 — Application shell

Implement:

```text
Sidebar
Topbar
Page container
Connection indicator placeholder
```

Routes:

```text
/
/factory
/fleet
/tasks
/analytics
/scenarios
```

## FE-003 — Define frontend contracts

Create Zod/types for:

```text
Robot
RobotTelemetry
Task
Metrics
Alert
WebSocketEvent
```

## FE-004 — Static operations dashboard

Fixture-driven:

```text
KPI cards
Fleet summary
Recent alerts
Task summary
```

## FE-005 — REST client

Implement:

```text
getRobots
getTasks
getMetrics
getAlerts
```

## FE-006 — Zustand store

State:

```text
robots
tasks
metrics
alerts
connection status
```

## FE-007 — WebSocket client

Requirements:

```text
connect
validate
route events
reconnect
cleanup
connection state
```

## FE-008 — 2D factory map

Render:

```text
Battery Buffer
Marriage Station
Charging Station
5 AMRs
```

## FE-009 — Realtime map integration

Acceptance:

> Mock backend movement is visible in the factory map.

## FE-010 — Fleet page

Implement table, filters, status and detail drawer.

## FE-011 — Task page

Implement task table and detail view.

## FE-012 — Alerts

Implement persistent alert list and severity UI.

---

# 39. Do not work on yet

Avoid spending the first sprint on:

```text
Photorealistic 3D
Advanced animations
ROS
Gazebo
Authentication
Complex role permissions
CAD layout editor
AI chatbot
Predictive maintenance
Mobile optimization
Fancy marketing landing page
```

Priority is realtime operations state.

---

# 40. End-to-end success scenario

The first important frontend demo should work like this:

```text
User opens dashboard
        │
        ▼
Frontend GETs factory snapshot
        │
        ▼
5 AMRs appear
        │
        ▼
WebSocket connects
        │
        ▼
LIVE indicator appears
        │
        ▼
Mock backend changes AMR-01 coordinates
        │
        ▼
AMR-01 moves on factory map
        │
        ▼
AMR-01 changes PICKING → DELIVERING
        │
        ▼
Fleet list updates
        │
        ▼
Battery drops below threshold
        │
        ▼
Warning appears
        │
        ▼
Task completes
        │
        ▼
Metrics update
```

If this works, the frontend is architecturally ready for later ROS2/Gazebo integration.

---

# 41. Definition of Done for frontend PRs

```text
[ ] Requirement implemented
[ ] TypeScript build passes
[ ] Lint passes
[ ] Tests added or updated
[ ] Tests pass
[ ] npm run build passes
[ ] CI green
[ ] No hardcoded backend URL outside env/config
[ ] No backend business logic duplicated in FE
[ ] Loading/error states considered where relevant
[ ] Contract changes documented
[ ] PR reviewed by another team member
```

---

# 42. Immediate implementation order

Work in exactly this order:

```text
1. feat/frontend-foundation
       ↓
2. Static UI with fixtures
       ↓
3. REST initial-state integration
       ↓
4. WebSocket realtime integration
       ↓
5. 2D moving AMRs
       ↓
6. Fleet/tasks/alerts polish
       ↓
7. Analytics
       ↓
8. Scenario controls
```

The first technical checkpoint is:

> **Five mock AMRs move in realtime on the browser, users can inspect their current state, and the UI remains usable if the WebSocket disconnects temporarily.**

Do not block this milestone on 3D, ROS2, Gazebo, authentication, or database work.
