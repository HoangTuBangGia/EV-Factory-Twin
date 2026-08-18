# EV Factory Digital Twin — Frontend Implementation Guide

> **Project:** EV Factory Digital Twin — AMR-based Battery Intralogistics
> **App:** RAV-11 Factory Twin
> **Scope:** Frontend only
> **Current phase:** Web MVP — Supabase Auth + RBAC, REST snapshot, WebSocket realtime, 2D/3D factory twin, scenario sandbox, admin console. **No ROS2, no Gazebo telemetry yet** (simulator is the backend MockFactory).
> **Frontend stack:** Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS v4 + Zustand 5 + Zod 4 + ECharts 6 + Three.js (React Three Fiber / drei) + Supabase SSR + Vitest + Playwright

---

## 1. Frontend objective

The frontend turns factory state and telemetry received from the backend into a clear, real-time Digital Twin interface.

The frontend does **not** need to know whether telemetry comes from the mock engine, Gazebo, ROS2, or a real robot. It depends only on a stable backend contract:

```text
Telemetry Source
    │
    ├── Mock now (backend MockFactory)
    ├── ROS2 later
    └── Replay later
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

The source is selected at build/runtime through `NEXT_PUBLIC_DATA_SOURCE`:
- `api` → REST snapshot + WebSocket realtime.
- anything else (or unset) → bundled development fixtures (`src/lib/fixtures.ts`) plus a local simulated telemetry ticker (`useMockTelemetry`), with connection status `MOCK`.

---

## 2. Product context

The system represents the battery intralogistics area of an electric vehicle final-assembly factory. AMRs transport battery packs from the Battery Buffer to the Battery Marriage Station.

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

The frontend helps users answer:

- Where are all AMRs right now?
- Which AMR is carrying which battery pack?
- What task is each AMR performing?
- Which robots are idle, charging, waiting, or in error?
- Are any batteries low?
- What is current throughput?
- Are there active alerts?
- Can the user inspect a specific AMR or task?

Factory layout (20 m × 15 m) is mirrored in `src/lib/factory-layout.ts` and must stay in sync with `apps/backend/src/ev_twin_api/core/layout.py`. Station anchors, zones, and the main route are defined there.

---

## 3. Frontend responsibilities

Frontend owns:

1. Application shell and navigation (sidebar is permission-filtered).
2. Authentication with Supabase (login/logout, session restore, token refresh, expiry/revocation handling).
3. RBAC — role → permission mapping drives nav and action gating.
4. Dashboard presentation.
5. Factory map / Digital Twin visualization (WebGL 3D with SVG 2D fallback).
6. Real-time WebSocket connection (auth handshake, backoff reconnect, snapshot resync).
7. Initial data loading through REST (`fetchFactorySnapshot`).
8. Client-side state management (Zustand).
9. Robot fleet visualization and robot detail drawer.
10. Task list.
11. KPI cards and ECharts trends.
12. Alerts panel.
13. Loading, empty, offline, and error states.
14. Scenario sandbox: run SimPy benchmark, review (approve/reject), apply approved scenario.
15. Admin console: user role/status management, Supabase invites, business audit table.
16. Frontend unit tests (Vitest) and browser E2E (Playwright).

Frontend does **not** own:

- robot task assignment logic;
- battery drain calculation;
- throughput calculation;
- task generation;
- collision detection;
- factory simulation logic;
- robot path planning;
- KPI formulas;
- scenario approval policy.

These values and decisions come from the backend.

---

## 4. Directory structure (current)

```text
apps/frontend/
├── .env.example                     # NEXT_PUBLIC_* variables (see §8)
├── Dockerfile                       # empty — no container image yet
├── e2e/
│   └── hosted-rbac.spec.ts          # Playwright hosted-Supabase RBAC suite
├── playwright.config.ts             # boots FastAPI + Next.js; chromium only
├── next.config.ts
├── package.json
├── tsconfig.json                    # strict, path alias @/* -> ./src/*
├── vitest.config.ts
├── src/
│   ├── middleware.ts                # edge auth guard (redirects, admin check)
│   ├── app/
│   │   ├── layout.tsx               # root layout: AuthProvider + ApplicationFrame
│   │   ├── page.tsx                 # "/" Overview dashboard
│   │   ├── login/page.tsx           # /login (public)
│   │   ├── factory/page.tsx         # /factory — full 2D twin + alerts
│   │   ├── fleet/page.tsx           # /fleet — fleet table + drawer
│   │   ├── tasks/page.tsx           # /tasks — task lifecycle table
│   │   ├── analytics/page.tsx       # /analytics — KPI + ECharts trends
│   │   ├── scenarios/page.tsx       # /scenarios — benchmark + review + apply
│   │   ├── admin/page.tsx           # /admin — users, invite, audit (ADMIN)
│   │   ├── forbidden/page.tsx       # /forbidden — 403
│   │   ├── scene-probe/page.tsx     # /scene-probe — dev-only 3D, no auth
│   │   └── globals.css              # Tailwind + bespoke component CSS
│   ├── components/
│   │   ├── admin/                   # admin-user-table, audit-table, invite-user-form
│   │   ├── alerts/                  # alert-list (severity-coded feed)
│   │   ├── auth/                    # auth-provider, login-form, access-denied
│   │   ├── charts/                  # operations-chart (ECharts)
│   │   ├── dashboard/               # kpi-grid
│   │   ├── factory/                 # factory-map, factory-map-2d, scene/* (3D)
│   │   ├── fleet/                   # fleet-table, robot-drawer, battery, status-badge
│   │   ├── layout/                  # application-frame, data-provider, sidebar, topbar
│   │   ├── scenarios/               # scenario-actions, scenario-comparison
│   │   └── tasks/                   # task-table
│   ├── hooks/
│   │   ├── use-factory-socket.ts    # WebSocket lifecycle + snapshot sync
│   │   ├── use-initial-factory-data.ts
│   │   └── use-mock-telemetry.ts    # mock-mode simulated ticker
│   ├── lib/
│   │   ├── api-client.ts            # typed REST client (zod-validated)
│   │   ├── websocket-client.ts      # FactorySocket (auth handshake, backoff)
│   │   ├── env.ts                   # SINGLE source of all env access
│   │   ├── coordinate.ts            # FACTORY_SIZE, worldToScreen
│   │   ├── factory-layout.ts        # station anchors, zones, routes
│   │   ├── factory-snapshot.ts      # 4 parallel REST calls + timeout + commit
│   │   ├── fixtures.ts              # mock robots/tasks/metrics/alerts/history
│   │   ├── auth/                    # permissions.ts, return-to.ts
│   │   └── supabase/                # client.ts, middleware.ts, server.ts
│   ├── schemas/                     # zod schemas (see §5)
│   │   ├── robot.ts  task.ts  metric.ts  alert.ts  scenario.ts
│   │   ├── auth.ts  admin.ts  factory.ts  websocket-event.ts
│   ├── stores/
│   │   └── factory-store.ts         # Zustand store
│   └── test/
│       └── setup.ts                 # jest-dom matchers + cleanup
```

---

## 5. Core data contracts (zod schemas)

All contracts live in `src/schemas/` and are validated with **Zod**. Types are derived with `z.infer`. The backend contract is documented in `docs/api.md` — keep both in sync.

### 5.1 Robot status (`schemas/robot.ts`)

```ts
export const robotStatusSchema = z.enum([
  "IDLE", "MOVING_TO_PICKUP", "PICKING", "DELIVERING", "DROPPING",
  "MOVING_TO_CHARGER", "WAITING", "CHARGING", "ERROR", "OFFLINE",
]);
```

Do not invent frontend-only status names.

### 5.2 Robot (`schemas/robot.ts`)

```ts
export const robotSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: robotStatusSchema,
  battery: z.number().min(0).max(100),
  pose: z.object({ x: z.number(), y: z.number(), yaw: z.number() }),
  velocity: z.object({ linear: z.number(), angular: z.number() }),
  task_id: z.string().nullable(),
  payload_id: z.string().nullable(),
  last_seen_at: z.string(),
});
```

### 5.3 RobotTelemetry (`schemas/robot.ts`)

WebSocket `robot.telemetry` payload; ~10 Hz per active robot.

```ts
export const robotTelemetrySchema = z.object({
  timestamp: z.string(),
  robot_id: z.string(),
  pose: poseSchema,
  velocity: velocitySchema,
  battery: z.number().min(0).max(100),
  status: robotStatusSchema,
  task_id: z.string().nullable(),
  payload_id: z.string().nullable(),
});
```

### 5.4 Task (`schemas/task.ts`)

```ts
export const taskStatusSchema = z.enum([
  "QUEUED", "ASSIGNED", "PICKUP", "IN_PROGRESS", "DELIVERED", "COMPLETED", "FAILED",
]);

export const taskSchema = z.object({
  task_id: z.string(),
  type: z.literal("DELIVER_BATTERY"),
  payload_id: z.string(),
  pickup: z.string(),
  dropoff: z.string(),
  assigned_robot_id: z.string().nullable(),
  status: taskStatusSchema,
  created_at: z.string(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
});
```

### 5.5 FactoryMetrics (`schemas/metric.ts`)

```ts
export const factoryMetricsSchema = z.object({
  completed_tasks: z.number(),
  throughput_per_hour: z.number(),
  average_cycle_time_seconds: z.number(),
  active_tasks: z.number(),
  queued_tasks: z.number(),
  starvation_events: z.number(),
  fleet_utilization_percent: z.number(),
});
```

Frontend does **not** calculate these business metrics from telemetry — backend owns the formulas.

### 5.6 Alert (`schemas/alert.ts`)

```ts
export const alertSeveritySchema = z.enum(["INFO", "WARNING", "CRITICAL"]);
export const factoryAlertSchema = z.object({
  id: z.string(), severity: alertSeveritySchema, code: z.string(), message: z.string(),
  robot_id: z.string().nullable(), task_id: z.string().nullable(), timestamp: z.string(),
});
```

### 5.7 Scenario (`schemas/scenario.ts`)

```ts
export const scenarioStatusSchema = z.enum(["DRAFT", "SIMULATED", "APPROVED", "REJECTED", "APPLIED"]);

export const scenarioConfigSchema = z.object({
  num_robots: z.number().int().min(1).max(10),
  num_tasks: z.number().int().min(1).max(10_000),
  task_arrival_interval: z.number().min(1).max(60),
  travel_time: z.number().positive().max(86_400),
  loading_time: z.number().positive().max(86_400),
  simulation_time: z.number().positive().max(86_400),
});

export const scenarioRunRequestSchema = scenarioConfigSchema.extend({
  name: z.string().trim().min(1, "Name is required").max(80),
});

export const scenarioSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  status: scenarioStatusSchema,
  config: scenarioConfigSchema,
  metrics: scenarioMetricsSchema,
  duration_ms: z.number().nonnegative(),
  created_at: utcDateTimeSchema,            // ends with "Z"
  created_by: z.string().uuid().nullable(),
  reviewed_at: utcDateTimeSchema.nullable(),
  reviewed_by: z.string().uuid().nullable(),
  applied_at: utcDateTimeSchema.nullable(),
  applied_by: z.string().uuid().nullable(),
  version: z.number().int().min(1),
});
```

### 5.8 Auth & RBAC (`schemas/auth.ts`)

```ts
export const appRoleSchema = z.enum(["DESIGNER", "MONITOR", "ADMIN"]);

export const currentUserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  display_name: z.string().min(1),
  role: appRoleSchema,
  is_active: z.boolean(),
});
```

### 5.9 Admin (`schemas/admin.ts`)

`AdminUser`, `AdminUserUpdate`, `AdminInviteRequest`, `AuditAction` enum, and `AuditEvent`. Audit actions: `SCENARIO_RUN`, `SCENARIO_APPROVED`, `SCENARIO_REJECTED`, `SCENARIO_APPLIED`, `FACTORY_RESET`, `ROLE_CHANGED`, `USER_DISABLED`, `USER_ENABLED`, `USER_INVITED`.

### 5.10 WebSocket events (`schemas/websocket-event.ts`)

```ts
export const factoryEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("robot.telemetry"), data: robotTelemetrySchema }),
  z.object({ type: z.literal("task.updated"), data: taskSchema }),
  z.object({ type: z.literal("metrics.updated"), data: factoryMetricsSchema }),
  z.object({ type: z.literal("alert.created"), data: factoryAlertSchema }),
  z.object({ type: z.literal("factory.reset"), data: z.null() }),
]);
```

---

## 6. REST API used by the frontend

Base URL comes from `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`). All HTTP is centralized in `src/lib/api-client.ts` — components never call raw `fetch` directly.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/auth/me` | Current user/profile/role |
| GET | `/api/v1/factory` | Factory layout |
| GET | `/api/v1/robots` | All AMRs |
| GET | `/api/v1/robots/{id}` | One AMR |
| GET | `/api/v1/tasks` | All tasks |
| GET | `/api/v1/tasks/{id}` | One task |
| GET | `/api/v1/metrics` | Factory metrics |
| GET | `/api/v1/alerts` | Alerts |
| POST | `/api/v1/mock/config` | Update mock simulation parameters |
| POST | `/api/v1/mock/reset` | Reset mock factory state |
| GET | `/api/v1/scenarios/baseline` | Repository baseline scenario |
| GET | `/api/v1/scenarios` | Candidate list |
| GET | `/api/v1/scenarios/{id}` | One scenario |
| POST | `/api/v1/scenarios/run` | Run SimPy benchmark |
| POST | `/api/v1/scenarios/{id}/approve` | Approve (Monitor) |
| POST | `/api/v1/scenarios/{id}/reject` | Reject (Monitor) |
| POST | `/api/v1/scenarios/{id}/apply` | Apply to mock factory (Monitor) |
| GET | `/api/v1/admin/users` | Users (ADMIN) |
| PATCH | `/api/v1/admin/users/{id}` | Change role/status (ADMIN) |
| POST | `/api/v1/admin/users/invite` | Supabase invite (ADMIN) |
| GET | `/api/v1/admin/audit?limit=N` | Business audit (ADMIN) |

`apiClient` injects `Authorization: Bearer <access-token>` when available. A `401` invokes the global unauthorized handler (session expiry). Responses are validated with the corresponding zod schema.

`fetchFactorySnapshot` (`src/lib/factory-snapshot.ts`) issues the four initial reads (`robots`, `tasks`, `metrics`, `alerts`) in parallel with a 10 s timeout and forwards abort signals; `commitFactorySnapshot` writes the result into the store.

---

## 7. WebSocket contract

Endpoint from `NEXT_PUBLIC_WS_URL` (default `ws://localhost:8000/ws/factory`).

### 7.1 Auth handshake

After `open`, the client sends the first message — the Supabase access token. The socket is **not** added to the broadcast pool until authenticated:

```json
{ "type": "auth", "access_token": "<supabase-access-token>" }
```

The server replies within 5 s:

```json
{
  "type": "auth.ok",
  "data": {
    "user_id": "…", "display_name": "…", "role": "MONITOR", "expires_at": 1786676400
  }
}
```

`expires_at` is a Unix epoch (seconds). The client only enters `LIVE` after `auth.ok`.

### 7.2 Events

After `auth.ok`, every message is wrapped in the envelope `{ "type", "data" }` (see §5.10):

| `type` | `data` schema | Frequency |
|---|---|---|
| `robot.telemetry` | `RobotTelemetry` | ~10 Hz per robot |
| `task.updated` | `Task` | event-driven |
| `metrics.updated` | `FactoryMetrics` | ~1 Hz wall clock |
| `alert.created` | `FactoryAlert` | event-driven |
| `factory.reset` | `null` | on `POST /api/v1/mock/reset` or scenario apply |

### 7.3 Close codes handled by the client

| Code | Meaning | Client behavior |
|---:|---|---|
| `4401` | Unauthorized / bad token | `refreshSession()` once per token; else invalidate |
| `4403` | Forbidden / inactive profile | `invalidateSession()` → login with `reason=access_revoked` |
| `4409` | Profile changed | `refreshUser()` then reconnect |
| `1008` | Origin policy violation | stop (no reconnect) |
| `4001`–`4004` | Client-side private codes | backoff reconnect / protocol stop |

### 7.4 Reconnect and resync (`FactorySocket` in `src/lib/websocket-client.ts`)

- Exponential backoff: 1 s → 10 s cap.
- Events received while a snapshot is synchronizing are buffered (limit 1000) and replayed after sync.
- A `factory.reset` invalidates an in-flight REST snapshot and triggers re-sync.
- After every `auth.ok` the store re-fetches the REST snapshot (deterministic, cheap) to close missed-event gaps.
- Status transitions: `CONNECTING` → `LIVE` → `OFFLINE` (retry) → `LIVE`. Never require a browser refresh after backend restart. Status is always shown as text (plus dot) in the topbar, never color alone.

---

## 8. Environment variables

All `process.env.NEXT_PUBLIC_*` reads are centralized in `src/lib/env.ts` — it is the only file that touches them. `apps/frontend/.env.example`:

```env
NEXT_PUBLIC_DATA_SOURCE=api
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/factory
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
```

Defaults if unset: `dataSource` → `"mock"`, API → `http://localhost:8000`, WS → `ws://localhost:8000/ws/factory`. Supabase vars have no default; when missing, `getSupabaseConfig()` returns `null` and the app shows an "authentication not configured" error state.

Playwright E2E additionally reads `DESIGNER_EMAIL/PASSWORD`, `MONITOR_EMAIL/PASSWORD`, `ADMIN_EMAIL/PASSWORD`, `E2E_EXTERNAL_SERVERS`, `E2E_BASE_URL`, `E2E_API_URL` (see `playwright.config.ts`).

---

## 9. Authentication & RBAC

Supabase Auth via `@supabase/ssr`; roles live server-side in the `profiles` table (`role`, `is_active`) and are read by the backend (`/api/v1/auth/me`).

### 9.1 Files

- `src/lib/supabase/client.ts` — browser client singleton (`createBrowserClient`).
- `src/lib/supabase/middleware.ts` — `createServerClient` session refresh + optional role lookup.
- `src/lib/supabase/server.ts` — server client for RSC.
- `src/middleware.ts` — edge middleware: refreshes session on every request; redirects unauthenticated users to `/login?returnTo=…`; `/admin*` additionally checks role and redirects non-ADMIN to `/forbidden`; sets `Cache-Control: private, no-store`. Matcher excludes `scene-probe`, `_next/static`, `_next/image`, `favicon.ico`, and image assets.
- `src/components/auth/auth-provider.tsx` — client context: login/logout, session hydration, `onAuthStateChange`, token refresh, expiry/revocation handling, API token injection (`setApiAccessToken`), factory-store reset on logout.

### 9.2 Permission matrix (`src/lib/auth/permissions.ts`)

```ts
DESIGNER: operations:view, scenarios:view, scenarios:run, layout:edit
MONITOR:  operations:view, scenarios:view, scenarios:review, scenarios:apply, factory:control
ADMIN:    operations:view, scenarios:view, users:manage, audit:view
```

`can(role, permission)` gates sidebar links and in-page actions. Note `ADMIN` is administrative and is **not** allowed to run/review/apply scenarios.

### 9.3 Login flow

- `/login` accepts `returnTo` (open-redirect protected by `safeReturnTo`) and `reason` (`session_expired` / `access_revoked`).
- Role-based default redirect: DESIGNER → `/scenarios`, ADMIN → `/admin`, MONITOR → `/`.
- 401/403 from the API surface as clear errors; expired sessions redirect to login with the correct reason.
- `ApplicationFrame` bypasses the protected shell only for `/login` and `/scene-probe`.

---

## 10. Zustand store (`src/stores/factory-store.ts`)

```ts
robots: Record<string, Robot>;          // keyed by robot id
tasks: Record<string, Task>;            // keyed by task_id
metrics: FactoryMetrics | null;
metricsHistory: MetricsSample[];        // sampled every 5s, window 5 min
alerts: FactoryAlert[];                 // capped at 50
selectedRobotId: string | null;
connectionStatus: "CONNECTING" | "LIVE" | "OFFLINE" | "MOCK";
```

Actions: `setRobots`, `updateRobotTelemetry`, `setTasks`, `updateTask`, `setMetrics` (+ history sampling), `clearMetricsHistory`, `setAlerts`, `addAlert`, `selectRobot`, `setConnectionStatus`, `reset`.

Notes:

- Prefer `Record<string, Robot>` over arrays for realtime updates.
- `setMetrics` appends to `metricsHistory` only when the 5 s wall-clock sampling interval has elapsed, so telemetry bursts (e.g. high simulation speed) never re-render ECharts per event.
- Metrics history window is 5 minutes, so the ECharts trend is bounded.

### 10.1 Data flow

```text
REST snapshot (robots/tasks/metrics/alerts)
        │
        ▼
  Zustand Store  ◀── WebSocket events (incremental)
        ▲
        │
   React components (selective subscriptions)
```

Mock mode uses `src/lib/fixtures.ts` for the initial snapshot and `useMockTelemetry` (200 ms interval) to animate moving robots.

---

## 11. Pages

| Route | Access | Contents |
|---|---|---|
| `/` | auth | KPI grid, `FactoryMap`, compact fleet table, recent alerts (3), operations trend chart, robot drawer |
| `/factory` | auth | Full-size `FactoryMap view="2d"`, live alerts feed, layer filter buttons, robot drawer |
| `/fleet` | auth | Full fleet table with filters (ALL/ACTIVE/IDLE/CHARGING/WARNING/ERROR), robot drawer (battery/speed/pose/task/payload) |
| `/tasks` | auth | Task table with status badges, pickup/dropoff, duration |
| `/analytics` | auth | KPI grid + throughput and cycle-time ECharts trends |
| `/scenarios` | auth + RBAC | Designer run form, scenario history tabs, baseline vs candidate comparison, provenance, approve/reject/apply |
| `/admin` | ADMIN only | User table (role change, enable/disable), Supabase invite form, audit table |
| `/forbidden` | auth | 403 access-denied panel |
| `/scene-probe` | dev only | Fixed 1440×900 3D scene with canned robot poses (no auth) |
| `/login` | public | Email/password form |

### 11.1 Factory map (`FactoryMap`)

- WebGL detection at runtime; renders the React Three Fiber `FactoryScene` when available, otherwise falls back to the SVG `FactoryMap2D`.
- `/` defaults to auto (3D when WebGL exists), `/factory` forces `2d`.
- 3D scene: sealed-concrete floor with metre grid, building shell, route lanes, battery buffer rack, marriage station, charging station, no-go zone, AMR meshes, contact shadows, orbit camera with reset. All textures are procedural (canvas) — no image assets in `public/`.
- Robots read exclusively from the central store; no per-mesh network calls.

### 11.2 Scenario sandbox (`/scenarios`)

Full Designer → Monitor → Admin loop:

1. **Designer** fills the run form (`scenarioRunRequestSchema`), calls `POST /scenarios/run`.
2. Candidate appears as `SIMULATED` with baseline-vs-candidate comparison table.
3. **Monitor** approves or rejects a `SIMULATED` candidate.
4. **Monitor** applies an `APPROVED` candidate → mock factory resets (confirm dialog), redirects to `/factory`.

Role-gated: designers cannot review/apply their own scenario; ADMIN is read-only. Workflow provenance (created/reviewed/applied by whom, version) is displayed.

### 11.3 Admin console (`/admin`)

- `AdminUserTable` with role select + enable/disable, guarded against disabling the last active admin (409 surfaced).
- `InviteUserForm` → `POST /admin/users/invite` (501/503 when the Supabase Admin integration is unavailable).
- `AuditTable` — latest 100 business audit events.

---

## 12. Coordinate system

- Backend coordinates are factory meters, not pixels. Factory is 20 m × 15 m (`FACTORY_SIZE` in `src/lib/coordinate.ts`).
- `worldToScreen(x, y, …)` converts meters → pixels for the SVG map (y flipped).
- `toScene(point, height)` in `src/lib/factory-layout.ts` converts factory meters (y = north) → scene units (y = up, floor centred on origin) for the 3D map.
- Keep this single convention; components never convert themselves.

---

## 13. Status conventions & UI states

Semantic status pairing (color + text always together):

```text
IDLE               neutral
MOVING_TO_PICKUP   active
PICKING            active
DELIVERING         active
DROPPING           active
MOVING_TO_CHARGER  active
WAITING            warning
CHARGING           info
ERROR              critical
OFFLINE            muted
```

Every REST-powered section provides loading / success / empty / error states. When the WebSocket drops but snapshot data exists, the UI stays populated with `OFFLINE` status — it never blanks out. Invalid WebSocket payloads are logged in development and ignored; they never crash the dashboard.

---

## 14. Testing

### 14.1 Unit / component tests (Vitest)

- Config `vitest.config.ts`; setup `src/test/setup.ts` (jest-dom + cleanup).
- Tests live next to source (`*.test.ts(x)`): api-client, websocket-client, factory-snapshot, factory-layout, permissions, return-to, store, kpi-grid, fleet-table, battery, operations-chart, scenario-actions, scenario-comparison, login-form, auth-provider, factory-map, middleware, and page tests.

```bash
cd apps/frontend
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

### 14.2 Browser E2E (Playwright)

- `playwright.config.ts` boots FastAPI + Next.js servers locally (or uses `E2E_EXTERNAL_SERVERS=true`).
- `e2e/hosted-rbac.spec.ts` authenticates against a dedicated hosted Supabase project with real `DESIGNER`/`MONITOR`/`ADMIN` accounts. Skips (with the missing variable names) when credentials are absent.
- Trace, screenshot, and video are deliberately disabled — login requests contain passwords and responses contain tokens.
- Runs against the dedicated development Supabase project only, never production.

```bash
cd apps/frontend
npx playwright install chromium
npm run test:e2e:list
npm run test:e2e
```

---

## 15. CI

`.github/workflows/ci.yml` runs a `frontend` job: `npm ci` → `lint` → `typecheck` → `test --run` → `build` (build sets `NEXT_PUBLIC_DATA_SOURCE=api`). A separate `hosted-e2e` job runs Playwright only when the required repository secrets are present.

---

## 16. Definition of Done for frontend PRs

```text
[ ] Requirement implemented
[ ] TypeScript build passes
[ ] Lint passes
[ ] Tests added or updated
[ ] Tests pass
[ ] npm run build passes
[ ] CI green
[ ] No hardcoded backend URL outside env/config (src/lib/env.ts)
[ ] No backend business logic duplicated in FE
[ ] Loading/error/offline states considered where relevant
[ ] Contract changes documented (this guide + docs/api.md)
[ ] PR reviewed by another team member
```

---

## 17. Not in scope of the current MVP

```text
ROS / Gazebo telemetry ingestion
Photorealistic 3D
Advanced animations
CAD layout editor
AI chatbot
Predictive maintenance
Mobile optimization
```

The current milestone is:

> **Authenticated users watch five mock AMRs move in realtime on a 2D/3D factory twin, inspect fleet/tasks/analytics, run and review SimPy scenarios, and administrators manage roles and audit — all with a UI that remains usable if the WebSocket disconnects temporarily.**