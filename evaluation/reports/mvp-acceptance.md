# MVP Acceptance Record

## Decision

`PENDING`

This record intentionally contains no observations copied from the retired mock
UI demo. Complete it using one reviewed commit and one production-shaped
deployment set.

## Run identity

| Field | Value |
|---|---|
| Evaluation date/time (UTC) | |
| Commit SHA | |
| Evaluator | |
| Frontend deployment URL/ID | |
| Backend deployment URL/ID | |
| Supabase migration version | |
| Edge host/config checksum | |
| ROS 2 / Gazebo versions | |

## Automated gates

| Gate | Run URL or artifact | Result |
|---|---|---|
| Backend lint, format, migration, typecheck and tests | | `PENDING` |
| Database migration and persistence smoke | | `PENDING` |
| Frontend lint, typecheck, unit, browser smoke and build | | `PENDING` |
| ROS build and tests | | `PENDING` |
| Backend container build and health smoke | | `PENDING` |
| Hosted Designer/Monitor E2E | | `PENDING` |

## Functional acceptance

| ID | Mandatory observation | Evidence | Result |
|---|---|---|---|
| FA-01 | Designer creates an immutable layout version with stations, delivery/support routes, no-go and congestion zones | | `PENDING` |
| FA-02 | SimPy resolves route distance/congestion from that layout and reports all authoritative KPI | | `PENDING` |
| FA-03 | Baseline/candidate geometry and KPI are compared before submission | | `PENDING` |
| FA-04 | Designer cannot approve/apply; Monitor reviews and approves | | `PENDING` |
| FA-05 | Apply follows `PENDING → ACKNOWLEDGED → COMPLETED`; scenario becomes `APPLIED` only after success | | `PENDING` |
| FA-06 | At least `AMR-01` and `AMR-02` run independently in Gazebo/ROS 2 | | `PENDING` |
| FA-07 | Backend-created transport task reaches Fleet/Task Manager and completes pickup/delivery lifecycle | | `PENDING` |
| FA-08 | Both robots' canonical telemetry reaches FastAPI and the same browser 3D scene | | `PENDING` |
| FA-09 | Low battery, waiting, congestion or bridge disconnect produces a visible deduplicated alert | | `PENDING` |
| FA-10 | Edge-offline apply times out; explicit retry creates a new attempt and can complete after recovery | | `PENDING` |
| FA-11 | Layout, scenario, approval, commands, alerts, audit and telemetry survive backend restart | | `PENDING` |

## Scenario and KPI evidence

Record baseline and chosen candidate from the same immutable layout contract.

| Metric | Baseline | Candidate | Unit / direction |
|---|---:|---:|---|
| Completed tasks | | | count / higher |
| Unfinished tasks | | | count / lower |
| Completion rate | | | % / higher |
| Throughput | | | tasks/hour / higher |
| Average cycle time | | | seconds / lower |
| Average waiting time | | | seconds / lower |
| Fleet utilization | | | % / contextual |
| Starvation events | | | count / lower |
| Congestion | | | % / lower |
| Travel distance | | | metres / contextual |
| Average delivery delay | | | seconds / lower |

Chosen layout/version:  
Chosen route:  
Evaluated candidate count (must be `≤64`):  
Benchmark duration:  

## Realtime performance

Describe the sampling method and attach raw, sanitized results. Do not report a
single best-case sample as the benchmark.

| Measurement | Sample count | p50 | p95 | Maximum | Acceptance threshold | Result |
|---|---:|---:|---:|---:|---:|---|
| ROS timestamp → Backend ingress | | | | | defined before run | `PENDING` |
| Backend broadcast → Browser receipt | | | | | defined before run | `PENDING` |
| Browser 3D FPS on reference device | | | | | defined before run | `PENDING` |

Reference device/browser:  
Telemetry publish rate:  
Concurrent AMR count:  
Render quality mode:  

## Security and negative paths

| ID | Check | Evidence | Result |
|---|---|---|---|
| SEC-01 | Unauthenticated REST/WS cannot read telemetry | | `PENDING` |
| SEC-02 | Designer review/apply and Monitor run/edit return forbidden | | `PENDING` |
| SEC-03 | Edge ingress/command endpoints reject invalid shared secret | | `PENDING` |
| SEC-04 | CORS allows only the configured frontend origin | | `PENDING` |
| SEC-05 | Evidence contains no credentials, tokens or database URLs | | `PENDING` |

## Known limitations observed in this run

- 

## Sign-off

| Role | Name/identifier | Date | Decision |
|---|---|---|---|
| Designer representative | | | `PENDING` |
| Monitor representative | | | `PENDING` |
| Technical evaluator | | | `PENDING` |

Overall acceptance may become `PASS` only when every mandatory functional row,
all security checks and all pre-declared performance thresholds pass.
