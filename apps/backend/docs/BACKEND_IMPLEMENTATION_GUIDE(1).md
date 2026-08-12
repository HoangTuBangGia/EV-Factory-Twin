# EV Factory Digital Twin — Backend Implementation Guide

> **Project:** EV Factory Digital Twin — AMR-based Battery Intralogistics  
> **Scope:** Backend only  
> **Current phase:** Mock-data / Web MVP, **no ROS2, no Gazebo yet**  
> **Backend stack:** Python 3.12 + uv + FastAPI + Pydantic + WebSocket + pytest  
> **Persistence:** In-memory first; PostgreSQL/TimescaleDB later

## 1. Backend objective

The backend represents and simulates the operational state of the EV-factory battery intralogistics area and exposes that state to the frontend.

```text
Mock Factory Engine
        │
        ▼
 Factory Services
 ├── robot state
 ├── tasks
 ├── battery
 ├── metrics
 └── alerts
        │
   ┌────┴────┐
   ▼         ▼
 REST    WebSocket
   └────┬────┘
        ▼
     Frontend
```

The key requirement is:

> Replacing MOCK telemetry with ROS2 later must not require changing the frontend-facing contracts.

Backend owns domain state, validation, mock simulation, robot/task state machines, task assignment, movement, battery behavior, metrics, alerts, REST APIs, WebSocket, tests and OpenAPI docs.

Backend does **not** own frontend rendering, pixel coordinates, animations, ROS navigation or Gazebo physics.


## 2. Repository and package structure

Use the existing uv monorepo:

```text
P-078/
├── apps/backend/
├── packages/twin-core/
├── services/simulation/
├── evaluation/
├── pyproject.toml
└── uv.lock
```

Recommended backend structure:

```text
apps/backend/
├── pyproject.toml
├── src/ev_twin_api/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── health.py
│   │   ├── factory.py
│   │   ├── robots.py
│   │   ├── tasks.py
│   │   ├── metrics.py
│   │   ├── alerts.py
│   │   ├── mock.py
│   │   └── websocket.py
│   ├── schemas/
│   │   ├── robot.py
│   │   ├── telemetry.py
│   │   ├── task.py
│   │   ├── factory.py
│   │   ├── metrics.py
│   │   ├── alert.py
│   │   └── websocket.py
│   ├── services/
│   │   ├── factory_state.py
│   │   ├── mock_factory.py
│   │   ├── task_service.py
│   │   ├── metrics_service.py
│   │   ├── alert_service.py
│   │   └── websocket_manager.py
│   └── core/
│       └── config.py
└── tests/
    ├── api/
    ├── services/
    └── integration/
```

Layering:

```text
API Layer
   ↓
Service Layer
   ↓
Domain / State Layer
```

Do not put movement, battery or task-assignment logic directly inside API route handlers.


## 3. Core contracts

### Robot status

Use one enum everywhere:

```python
from enum import StrEnum

class RobotStatus(StrEnum):
    IDLE = "IDLE"
    MOVING_TO_PICKUP = "MOVING_TO_PICKUP"
    PICKING = "PICKING"
    DELIVERING = "DELIVERING"
    DROPPING = "DROPPING"
    MOVING_TO_CHARGER = "MOVING_TO_CHARGER"
    WAITING = "WAITING"
    CHARGING = "CHARGING"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"
```

Initial IDs:

```text
AMR-01
AMR-02
AMR-03
AMR-04
AMR-05
```

### Common models

```python
from datetime import datetime
from pydantic import BaseModel, Field

class Pose(BaseModel):
    x: float
    y: float
    yaw: float

class Velocity(BaseModel):
    linear: float
    angular: float

class Robot(BaseModel):
    id: str
    name: str
    status: RobotStatus
    pose: Pose
    velocity: Velocity
    battery: float = Field(ge=0, le=100)
    task_id: str | None = None
    payload_id: str | None = None
    last_seen_at: datetime
```

### Telemetry contract

This is the most important FE-BE contract:

```json
{
  "timestamp": "2026-08-11T04:00:00.125Z",
  "robot_id": "AMR-01",
  "pose": {"x": 12.4, "y": 7.8, "yaw": 1.57},
  "velocity": {"linear": 1.1, "angular": 0.0},
  "battery": 82.4,
  "status": "DELIVERING",
  "task_id": "TASK-0102",
  "payload_id": "BP-0102"
}
```

```python
class RobotTelemetry(BaseModel):
    timestamp: datetime
    robot_id: str
    pose: Pose
    velocity: Velocity
    battery: float = Field(ge=0, le=100)
    status: RobotStatus
    task_id: str | None
    payload_id: str | None
```

Do not rename fields casually after FE integration begins.


## 4. Factory model

Use deterministic coordinates in meters:

```text
Factory size         20m × 15m
Battery Buffer       (2, 4)
Intersection A       (8, 4)
Intersection B       (12, 8)
Marriage Station     (16, 8)
Charging Station     (2, 12)
Idle Zone            (5, 12)
```

Station:

```python
class Station(BaseModel):
    id: str
    name: str
    type: str
    x: float
    y: float
```

`GET /api/v1/factory` response example:

```json
{
  "width_m": 20,
  "height_m": 15,
  "stations": [
    {
      "id": "BATTERY_BUFFER",
      "name": "Battery Buffer",
      "type": "BUFFER",
      "x": 2,
      "y": 4
    },
    {
      "id": "MARRIAGE_STATION",
      "name": "Marriage Station",
      "type": "MARRIAGE",
      "x": 16,
      "y": 8
    }
  ]
}
```

Frontend converts meters to screen pixels; backend never returns pixel positions.


## 5. Task model and lifecycle

Main task type:

```text
DELIVER_BATTERY
```

```python
class TaskStatus(StrEnum):
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    PICKUP = "PICKUP"
    IN_PROGRESS = "IN_PROGRESS"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Task(BaseModel):
    task_id: str
    type: str = "DELIVER_BATTERY"
    payload_id: str
    pickup: str
    dropoff: str
    assigned_robot_id: str | None = None
    status: TaskStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
```

Lifecycle:

```text
QUEUED
  ↓ robot selected
ASSIGNED
  ↓
MOVING_TO_PICKUP
  ↓
PICKUP
  ↓
IN_PROGRESS
  ↓
DELIVERED
  ↓
COMPLETED
```

Robot state flow:

```text
IDLE
  ↓ task assigned
MOVING_TO_PICKUP
  ↓ arrived
PICKING
  ↓ pickup finished
DELIVERING
  ↓ arrived
DROPPING
  ↓ drop finished
IDLE
```

Charging flow:

```text
IDLE
  ↓ battery low
MOVING_TO_CHARGER
  ↓
CHARGING
  ↓ battery reaches target
IDLE
```


## 6. Mock movement engine

Do **not** teleport robots randomly. Use deterministic waypoint routes.

```python
ROUTES = {
    ("BATTERY_BUFFER", "MARRIAGE_STATION"): [
        (2, 4),
        (8, 4),
        (12, 8),
        (16, 8),
    ],
}
```

At each tick:

```text
distance_to_move = robot_speed * dt
```

Move toward the current waypoint. When the waypoint is reached, continue to the next.

Yaw:

```python
yaw = atan2(target_y - current_y, target_x - current_x)
```

Recommended update loop:

```text
10 Hz
```

Example:

```python
async def run(self) -> None:
    while self.running:
        started = time.monotonic()
        await self.tick(0.1 * self.config.simulation_speed)
        elapsed = time.monotonic() - started
        await asyncio.sleep(max(0.0, 0.1 - elapsed))
```

For production-quality timing later, use measured elapsed `dt`; this simple loop is sufficient for the first mock MVP.


## 7. Mock factory configuration

```python
class MockFactoryConfig(BaseModel):
    robot_count: int = Field(default=5, ge=1, le=10)
    task_interval_seconds: float = Field(default=8.0, ge=1.0, le=60.0)
    robot_speed_mps: float = Field(default=1.2, ge=0.1, le=3.0)
    simulation_speed: float = Field(default=1.0, ge=0.25, le=10.0)
    low_battery_threshold: float = Field(default=20.0, ge=0, le=100)
```

Task IDs and battery-pack IDs should be sequential:

```text
TASK-0001
TASK-0002

BP-0001
BP-0002
```

Every `task_interval_seconds`, create a new battery delivery task and put it in `QUEUED`.


## 8. Task scheduler

MVP algorithm:

1. Find robots in `IDLE`.
2. Remove robots whose battery is at/below threshold.
3. Calculate distance to Battery Buffer.
4. Choose the nearest eligible robot.
5. Assign the oldest queued task.

Pseudo-code:

```python
candidates = [
    robot
    for robot in robots.values()
    if robot.status == RobotStatus.IDLE
    and robot.battery > config.low_battery_threshold
]

if candidates:
    selected = min(
        candidates,
        key=lambda robot: distance(robot.pose, battery_buffer),
    )
```

If no AMR is available:

```text
task remains QUEUED
```

The scheduler retries later.

Do not implement advanced fleet optimization in this phase.


## 9. Battery and charging

A physical electrochemical model is not required.

Use accelerated demonstration parameters:

```text
MOVING             drains battery
PICKING/DROPPING   small drain
IDLE               negligible drain
CHARGING           increases battery
```

Rules:

```text
0 <= battery <= 100
low threshold = 20%
charge target = 80%
```

A low-battery AMR must not receive a new normal delivery task.

Document that battery rates are demo parameters, not physical battery-model claims.


## 10. FactoryState

Use one owner for mutable runtime state:

```python
class FactoryState:
    robots: dict[str, Robot]
    tasks: dict[str, Task]
    alerts: list[FactoryAlert]
    metrics: FactoryMetrics
    config: MockFactoryConfig
```

Responsibilities:

```text
initialize factory
read/update robots
add/update tasks
read metrics
add alerts
reset all mock state
return API snapshots
```

Do not scatter mutable global dictionaries across modules.

The current sprint is intentionally in-memory:

```text
backend restart → state reset
```

That is acceptable now. PostgreSQL comes later.


## 11. Metrics

```python
class FactoryMetrics(BaseModel):
    completed_tasks: int
    throughput_per_hour: float
    average_cycle_time_seconds: float
    active_tasks: int
    queued_tasks: int
    starvation_events: int
    fleet_utilization_percent: float
```

Definitions:

### Throughput

```text
completed tasks / elapsed simulated hours
```

Handle zero elapsed time safely.

### Average cycle time

For completed tasks:

```text
completed_at - created_at
```

Then average those durations.

### Fleet utilization

MVP definition:

```text
productive robots / total online robots × 100
```

Productive states:

```text
MOVING_TO_PICKUP
PICKING
DELIVERING
DROPPING
```

### Starvation

MVP definition:

```text
a queued delivery task waits longer than a configured threshold
```

A single task must not increment starvation on every tick. Record that its starvation event was already reported.


## 12. Alerts

```python
class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class FactoryAlert(BaseModel):
    id: str
    severity: AlertSeverity
    code: str
    message: str
    robot_id: str | None = None
    task_id: str | None = None
    timestamp: datetime
```

Initial codes:

```text
LOW_BATTERY
ROBOT_WAITING
TASK_BACKLOG
STARVATION
ROBOT_ERROR
```

Deduplicate stateful alerts. For example:

```text
LOW_BATTERY:AMR-01
```

should emit when AMR-01 enters the low-battery condition, not every 100 ms.


## 13. REST API

Use `/api/v1` except health.

```text
GET /health

GET /api/v1/factory

GET /api/v1/robots
GET /api/v1/robots/{robot_id}

GET /api/v1/tasks
GET /api/v1/tasks/{task_id}

GET /api/v1/metrics
GET /api/v1/alerts

POST /api/v1/mock/start
POST /api/v1/mock/stop
POST /api/v1/mock/reset
POST /api/v1/mock/config
```

Expected behavior:

```text
200 success
404 unknown robot/task
422 invalid Pydantic request
500 unexpected server failure
```

Unknown IDs should not return empty objects.

Mock config example:

```json
{
  "robot_count": 5,
  "task_interval_seconds": 8,
  "robot_speed_mps": 1.2,
  "simulation_speed": 1
}
```

Use response models so `/docs` remains an accurate FE-BE integration reference.


## 14. WebSocket

Endpoint:

```text
/ws/factory
```

Use an event envelope:

```json
{
  "type": "robot.telemetry",
  "data": {}
}
```

Initial event types:

```text
robot.telemetry
task.updated
metrics.updated
alert.created
factory.reset
```

Recommended frequencies:

```text
robot telemetry     10 Hz
metrics              1 Hz
task updates         event-driven
alerts               event-driven
```

Suggested manager:

```python
class WebSocketManager:
    async def connect(self, websocket: WebSocket) -> None:
        ...

    def disconnect(self, websocket: WebSocket) -> None:
        ...

    async def broadcast(self, payload: dict) -> None:
        ...
```

Requirements:

```text
multiple browser clients work
dead clients are removed
one disconnect does not break broadcast
serialization is consistent
```


## 15. FastAPI application lifecycle

Use FastAPI lifespan for the mock background engine:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await mock_factory.start()
    yield
    await mock_factory.stop()
```

`main.py` should mainly:

```text
create app
configure lifespan
configure CORS
include routers
```

Do not start background loops as module-import side effects.

Development origins:

```text
Frontend http://localhost:3000
Backend  http://localhost:8000
```

Configure CORS explicitly from environment/config.


## 16. Environment and dependency management

Suggested environment variables:

```env
APP_ENV=development
CORS_ORIGINS=http://localhost:3000
MOCK_FACTORY_ENABLED=true
MOCK_ROBOT_COUNT=5
MOCK_TASK_INTERVAL_SECONDS=8
MOCK_ROBOT_SPEED_MPS=1.2
MOCK_SIMULATION_SPEED=1
```

Dependencies must be managed with uv:

```bash
uv add --package ev-twin-api <dependency>
```

Do not use ad-hoc `pip install` as project dependency management.

Commit both when dependencies change:

```text
apps/backend/pyproject.toml
uv.lock
```


## 17. Logging

Useful INFO logs:

```text
factory started/stopped/reset
task created
task assigned
task completed
robot starts charging
low-battery condition entered
WebSocket connected/disconnected
```

Do **not** log every 10 Hz telemetry packet at INFO. Use DEBUG for high-frequency telemetry when needed.


## 18. Testing plan

Backend tests must cover business behavior, not just HTTP status codes.

Required groups:

```text
robot movement
robot state transitions
battery drain/charging
task generation
task assignment
task completion
metrics
starvation
alert deduplication
REST API
WebSocket
integration
```

### Assignment test

Given:

```text
AMR-01 distance=5m battery=80%
AMR-02 distance=2m battery=10%
AMR-03 distance=4m battery=70%
```

Expected:

```text
AMR-03 selected
```

### State-machine test

```text
IDLE + task
→ MOVING_TO_PICKUP
→ PICKING
→ DELIVERING
→ DROPPING
→ IDLE
```

Verify task status and payload attachment/detachment at each meaningful stage.

### Battery tests

```text
moving drains
charging increases
battery never <0
battery never >100
low-battery robot excluded from new tasks
```

### Metric test

If 2 tasks complete in 120 simulated seconds:

```text
throughput = 60 tasks/hour
```

If cycle times are 40s and 60s:

```text
average cycle time = 50s
```

### Alert test

```text
battery crosses below 20%
→ one alert

remains below 20%
→ no flood

recovers and later falls again
→ another alert may be created
```

### API tests

```text
GET /health → 200
GET /factory → valid map
GET /robots → five robots
GET unknown robot → 404
GET /tasks → valid schema
GET /metrics → valid schema
POST invalid mock config → 422
```

### WebSocket tests

```text
client connects
mock emits telemetry
client receives robot.telemetry
client disconnect does not crash app
```


## 19. CI and quality gates

Before opening a PR:

```bash
make check
```

Must pass:

```text
Ruff
Ruff format --check
Mypy
Pytest
```

GitHub Actions must be green.

Suggested project-level evaluation targets later:

```text
telemetry update >= 10 Hz
API p95 local < 200 ms
telemetry-to-web p95 target < 150 ms
```

These are project targets, not industry-standard claims.


## 20. Backend implementation roadmap

### BE-0 — Package structure

```text
[ ] api/
[ ] schemas/
[ ] services/
[ ] core/
[ ] health still works
[ ] make check passes
```

### BE-1 — Domain contracts

Implement and test:

```text
RobotStatus
Robot
RobotTelemetry
TaskStatus
Task
Station
FactoryMetrics
FactoryAlert
MockFactoryConfig
```

### BE-2 — FactoryState

```text
[ ] five AMRs
[ ] stations
[ ] task collection
[ ] metrics state
[ ] alerts
[ ] reset behavior
```

### BE-3 — REST snapshots

```text
[ ] GET /factory
[ ] GET /robots
[ ] GET /robots/{id}
[ ] GET /tasks
[ ] GET /tasks/{id}
[ ] GET /metrics
[ ] GET /alerts
```

### BE-4 — Mock movement

```text
[ ] 10 Hz loop
[ ] waypoint route
[ ] x/y changes
[ ] yaw changes
[ ] velocity
[ ] clean start/stop
```

Acceptance:

> Five robots can exist in memory and at least one robot moves deterministically through the factory.

### BE-5 — Task engine

```text
[ ] periodic task creation
[ ] queue
[ ] nearest eligible AMR assignment
[ ] pickup
[ ] delivery
[ ] dropoff
[ ] completion
```

Acceptance:

> A battery delivery task completes end-to-end and the AMR returns to IDLE.

### BE-6 — WebSocket realtime

```text
[ ] /ws/factory
[ ] robot.telemetry
[ ] task.updated
[ ] factory.reset
[ ] multi-client support
```

Acceptance:

> A test/client receives changing AMR coordinates without polling.

### BE-7 — Battery + charging

```text
[ ] battery drain
[ ] threshold
[ ] MOVING_TO_CHARGER
[ ] CHARGING
[ ] charging target
[ ] return to IDLE
```

### BE-8 — Metrics

```text
[ ] completed tasks
[ ] throughput
[ ] average cycle
[ ] active tasks
[ ] queued tasks
[ ] starvation
[ ] fleet utilization
[ ] metrics.updated at ~1 Hz
```

### BE-9 — Alerts

```text
[ ] LOW_BATTERY
[ ] TASK_BACKLOG
[ ] STARVATION
[ ] deduplication
[ ] alert.created
```

### BE-10 — Mock control API

```text
[ ] start
[ ] stop
[ ] reset
[ ] config
```

### BE-11 — Integration test

```text
mock starts
→ task created
→ AMR assigned
→ AMR moves
→ telemetry broadcast
→ delivery completes
→ metrics change
```


## 21. Suggested GitHub issues

```text
BE-001 Backend package structure
BE-002 Define FE-BE domain contracts
BE-003 Implement FactoryState
BE-004 Implement factory REST endpoints
BE-005 Implement deterministic AMR movement
BE-006 Implement task scheduler/state machine
BE-007 Implement battery and charging
BE-008 Implement WebSocket manager
BE-009 Implement factory metrics
BE-010 Implement alert engine
BE-011 Implement mock-control endpoints
BE-012 Add backend integration tests
```

Keep PRs reasonably small rather than implementing all backend behavior in one branch.


## 22. End-to-end backend success scenario

```text
Backend starts
      ↓
5 AMRs initialized
      ↓
Mock engine runs
      ↓
TASK-0001 created
      ↓
AMR-02 selected
      ↓
AMR-02 moves to Battery Buffer
      ↓
PICKING
      ↓
BP-0001 attached
      ↓
DELIVERING
      ↓
AMR-02 moves to Marriage Station
      ↓
DROPPING
      ↓
TASK-0001 COMPLETED
      ↓
metrics updated
      ↓
AMR-02 returns IDLE
```

During movement:

```text
robot.telemetry
```

is continuously broadcast to frontend clients.

When appropriate:

```text
LOW_BATTERY
TASK_BACKLOG
STARVATION
```

events are generated without duplicate flooding.


## 23. Do not implement yet

Do not spend this sprint on:

```text
ROS2
Gazebo
Nav2
PostgreSQL
TimescaleDB
Redis
Kafka
Celery
microservices
Kubernetes
AI/ML
complex authentication
real path planning
physics collision simulation
```

First prove:

```text
STATE
+
BEHAVIOR
+
REST
+
WEBSOCKET
+
TESTS
```


## 24. Backend MVP acceptance criteria

```text
[ ] Backend starts through uv
[ ] /health returns 200

[ ] Factory endpoint works
[ ] Five mock AMRs initialize
[ ] Factory coordinates are deterministic

[ ] Mock engine starts/stops cleanly
[ ] Robot positions update
[ ] Yaw updates
[ ] Coordinates stay in factory bounds

[ ] Tasks generate
[ ] Tasks queue
[ ] Tasks assign
[ ] Tasks complete

[ ] Battery drains
[ ] Battery stays within 0..100
[ ] Low-battery robot is excluded from new deliveries
[ ] Charging works

[ ] Metrics calculate correctly
[ ] Alerts generate
[ ] Alerts are deduplicated

[ ] REST snapshot APIs work
[ ] WebSocket streams realtime data
[ ] Multiple WS clients work
[ ] Disconnects do not crash the server

[ ] Pydantic validation works
[ ] Unknown IDs return 404
[ ] OpenAPI docs match implementation

[ ] Unit tests exist
[ ] API tests exist
[ ] WebSocket tests exist
[ ] Integration test exists

[ ] Ruff passes
[ ] Format check passes
[ ] Mypy passes
[ ] Pytest passes
[ ] make check passes
[ ] GitHub Actions is green
```


## 25. Definition of Done for backend PRs

```text
[ ] Requirement implemented
[ ] Business logic is outside route handlers
[ ] Contracts are explicit
[ ] Tests added/updated
[ ] Ruff passes
[ ] Format check passes
[ ] Mypy passes
[ ] Pytest passes
[ ] CI green
[ ] No secrets committed
[ ] Dependencies managed with uv
[ ] uv.lock committed when needed
[ ] API/contract docs updated
[ ] PR reviewed by another team member
```


## 26. Coordination checklist with frontend

Before integration, both sides must agree on:

```text
[ ] RobotStatus enum
[ ] TaskStatus enum
[ ] RobotTelemetry schema
[ ] Robot REST schema
[ ] Task REST schema
[ ] Metrics schema
[ ] Alert schema
[ ] factory width/height
[ ] station coordinates
[ ] REST paths
[ ] WebSocket path
[ ] WebSocket event names
[ ] timestamp format
[ ] nullable fields
```

The most important integration boundary is `RobotTelemetry`.

Do not modify it casually once frontend realtime integration begins.

---

## 27. Immediate order of work

```text
1. Contracts
   ↓
2. FactoryState
   ↓
3. REST snapshots
   ↓
4. Mock movement
   ↓
5. Task lifecycle
   ↓
6. WebSocket
   ↓
7. Battery / charging
   ↓
8. Metrics
   ↓
9. Alerts
   ↓
10. Mock controls
   ↓
11. Integration tests
```

The first major checkpoint is:

> **Five AMRs exist in a deterministic factory state, one battery-delivery task can complete end-to-end, and a WebSocket client receives realtime AMR telemetry using the same contract the frontend will later use with ROS2.**
