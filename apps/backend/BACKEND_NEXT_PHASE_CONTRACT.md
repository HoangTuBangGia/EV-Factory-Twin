# Backend Next-Phase Contract

## 1. Mục đích

Tài liệu này là hợp đồng triển khai cho phần Backend ở giai đoạn tiếp theo của
EV Factory Digital Twin. Mục tiêu không phải mở rộng thêm nhiều CRUD, mà hoàn
thiện và chứng minh Backend trong vòng khép kín của nhóm:

```text
Layout → Gazebo/ROS 2 → telemetry → FastAPI → WebSocket → KPI/alerts
       → SimPy comparison → Monitor approval → durable command → ROS result
```

Backend phải bảo đảm dữ liệu từ MOCK và ROS dùng cùng contract, quyền phê duyệt
được kiểm tra tại server, trạng thái quan trọng được lưu bền vững và toàn bộ
đường cloud-edge có thể kiểm chứng bằng test hoặc evidence đo được.

## 2. Nguồn sự thật

Thứ tự ưu tiên khi có mâu thuẫn:

1. Source code, test, migration và contract đang chạy.
2. `docs/requirements.md` và `docs/backend-ros2-mvp.md`.
3. `docs/api.md` và ADR-0005 về Cloud Run, Cloud SQL, JWT nội bộ.
4. `docs/team-plan.md` và `docs/architecture.md`.
5. Các implementation guide, dev log và change log cũ chỉ dùng làm lịch sử.

Không tiếp tục thiết kế Render/Supabase trong ADR-0003/0004. Runtime mục tiêu là
Cloud Run FastAPI, Cloud SQL PostgreSQL 17 và GCE ROS 2/Gazebo edge.

## 3. Phạm vi sở hữu

Nhánh này chỉ thay đổi nội dung trong `apps/backend`.

Backend chịu trách nhiệm:

- FastAPI REST, WebSocket và machine-authenticated edge endpoints;
- xác thực JWT và phân quyền `DESIGNER`/`MONITOR` tại server;
- orchestration cho telemetry, task, alert, KPI, scenario và command;
- PostgreSQL repository integration từ phía ứng dụng;
- startup/shutdown, health, logging và observability của Backend;
- test unit, API và integration nằm trong `apps/backend`;
- container/runtime configuration thuộc `apps/backend`.

Không tự ý sửa trong nhánh này:

- `packages/twin-core` và công thức KPI authoritative;
- `services/simulation` và mô hình SimPy;
- `ros2_ws` và hành vi edge/fleet/task manager;
- `postgres/migrations`, frontend, root tooling hoặc tài liệu toàn repo.

Nếu một acceptance criterion cần thay đổi ngoài `apps/backend`, phải dừng tại
contract boundary, mô tả thay đổi cần phối hợp và thực hiện bằng checkpoint hoặc
nhánh riêng sau khi nhóm chấp thuận.

## 4. Kiến trúc bất biến

- Browser không giao tiếp trực tiếp với ROS DDS hoặc PostgreSQL.
- ROS/Gazebo gửi trạng thái qua trusted edge bridge đến Backend.
- Browser REST dùng JWT; edge endpoint dùng machine secret độc lập.
- REST dùng cho CRUD/query/command; WebSocket dùng cho realtime fan-out.
- MOCK và ROS chuẩn hóa về cùng telemetry/application contract.
- Backend không định nghĩa lại KPI authoritative đã thuộc `twin-core`.
- Scenario chỉ thành `APPLIED` sau ROS execution result thành công.
- Retry giữ nguyên `operation_id` và tạo attempt riêng, có giới hạn.
- Telemetry cũ hoặc timestamp tương lai không được ghi đè live snapshot mới hơn.
- Production tiếp tục dùng một Backend instance khi live state và WebSocket còn
  process-local. Không bật scale-out trước khi có durable coordination/pub-sub.

## 5. Hiện trạng được coi là baseline

Backend hiện đã có:

- JWT login, `/auth/me` và hai role `DESIGNER`/`MONITOR`;
- REST snapshot cho factory, robot, task, metrics và alerts;
- versioned layout API;
- scenario run, submit, approve, reject và apply;
- deterministic bounded optimization;
- durable command/attempt/acknowledgement/result/timeout/retry;
- authenticated telemetry, task update, bridge health và command edge path;
- WebSocket authentication và realtime events;
- stale telemetry, bridge disconnect, command timeout và congestion lifecycle;
- PostgreSQL repositories, runtime history, retention integration và KPI writer;
- production validation, Cloud SQL connection và Cloud Run container;
- test coverage cho các service và API chính.

Baseline này không đồng nghĩa toàn bộ hosted Gazebo-to-browser acceptance đã
được chứng minh. Test mock hoặc component test không thay thế networked run với
hai AMR thật trong Gazebo.

## 6. Cơ chế chống regression Phase 1

Phase 1 là baseline tương thích bắt buộc, không phải phần được phép viết lại khi
triển khai các checkpoint tiếp theo. Một thay đổi chỉ được chấp nhận khi giữ các
luồng cũ hoạt động hoặc có contract change được nhóm phê duyệt riêng.

### 6.1 Contract freeze

Nếu không có phê duyệt contract change, phải giữ tương thích với:

- URL, HTTP method, status code và ý nghĩa response của REST API hiện có;
- field bắt buộc, enum, đơn vị, timestamp và nullable semantics hiện có;
- WebSocket authentication handshake và các event type hiện có;
- hai role duy nhất `DESIGNER` và `MONITOR` cùng server-side authorization;
- lifecycle Robot, Task, Scenario và Command;
- quy tắc telemetry ordering theo `robot_id` và source timestamp;
- `operation_id`, attempt history, retry budget và idempotency của command;
- MOCK và ROS dùng cùng application contract;
- hành vi local fallback khi không cấu hình database trong development/test;
- production fail-fast và single-instance runtime boundary hiện tại.

Được phép thêm field response optional hoặc endpoint mới khi client cũ vẫn hoạt
động. Không được đổi tên/xóa field, đổi enum, nới quyền, đổi transition hoặc thay
đổi ý nghĩa dữ liệu dưới cùng một API version.

### 6.2 Baseline verification trước khi sửa

Trước mỗi checkpoint có thay đổi code:

1. Ghi lại commit SHA và trạng thái working tree.
2. Chạy targeted test của khu vực sắp sửa và lưu kết quả baseline.
3. Xác định các API, service, worker và repository caller bị ảnh hưởng.
4. Ghi rõ behavior Phase 1 phải giữ nguyên và negative path liên quan.
5. Nếu baseline đang đỏ, dừng và phân biệt lỗi có sẵn với lỗi của checkpoint;
   không sửa lẫn lỗi ngoài phạm vi chỉ để có kết quả xanh.

Không bắt đầu bằng refactor rộng. Ưu tiên sửa tại boundary nhỏ nhất đang sở hữu
behavior và tái sử dụng helper/service hiện có.

### 6.3 Regression test bắt buộc

Mọi bug hoặc thay đổi logic không tầm thường phải có test nhỏ nhất có thể chứng
minh lỗi trước khi sửa và pass sau khi sửa. Tùy vùng ảnh hưởng, test phải bao phủ:

- authentication: missing/invalid/expired token, inactive user và role mismatch;
- telemetry: robot isolation, stale sample, future skew và no broadcast on reject;
- WebSocket: auth trước broadcast, snapshot/reconnect và event envelope;
- scenario: deterministic run và transition guard;
- command: ACK/result, duplicate delivery, timeout, retry và late attempt result;
- persistence: restart/read-back, ordering và transaction failure behavior;
- runtime health: stale/disconnect/timeout alert dedupe, clear và retrigger;
- MOCK fallback: start/stop/reset/config và realtime behavior Phase 1;
- production config: fail-fast khi thiếu dependency hoặc secret bắt buộc.

Test mới phải dùng framework, fixture và pattern hiện có. Không tạo test
infrastructure mới nếu một focused service/API test đã đủ bảo vệ behavior.

### 6.4 Database và state compatibility

Trong phạm vi nhánh này:

- không sửa migration hoặc schema PostgreSQL;
- repository query mới phải hoạt động với schema/migration ledger hiện hành;
- không thay đổi hoặc xóa durable record của layout, scenario, KPI, command,
  alert, audit, task hay telemetry đã có;
- không cho sample cũ khôi phục đè live state mới hơn sau reconnect/restart;
- không biến process-local state thành nguồn sự thật thay cho durable lifecycle;
- failure giữa side effect và persistence phải fail rõ ràng, giữ audit/history và
  không báo trạng thái thành công giả.

Nếu cần migration, backfill hoặc thay đổi retention, dừng checkpoint và đề xuất
thay đổi ngoài `apps/backend` để nhóm review riêng.

### 6.5 Verification sau khi sửa

Trước khi bàn giao mỗi checkpoint:

1. Chạy lại targeted baseline tests và regression tests mới.
2. Chạy toàn bộ Backend quality gate phù hợp: Ruff, format check, Mypy và pytest.
3. Với thay đổi startup/container, chạy production configuration và container
   smoke check liên quan.
4. Với thay đổi persistence, chạy PostgreSQL-gated test trên database tạm phù hợp;
   không trình bày test bị skip như đã pass.
5. So sánh API/WebSocket response trước–sau cho contract bị ảnh hưởng.
6. Kiểm tra log và fixture không chứa credential hoặc production data.
7. Rà diff để xác nhận không có thay đổi ngoài `apps/backend`.

Checkpoint không được đánh dấu hoàn thành nếu Phase 1 test từng pass nay fail,
coverage của behavior bị xóa, quality gate bị hạ hoặc acceptance cũ chỉ còn hoạt
động nhờ thay đổi dữ liệu/fixture che lỗi.

### 6.6 Điều kiện dừng và rollback

Dừng checkpoint để nhóm quyết định khi:

- cần breaking API/WebSocket/schema change;
- cần sửa `twin-core`, SimPy, ROS, migration, frontend hoặc root tooling;
- kết quả mới mâu thuẫn KPI/lifecycle/role contract đã khóa;
- không thể giữ đồng thời MOCK fallback và ROS contract;
- thay đổi yêu cầu scale-out hoặc nhiều bridge ngoài single-instance baseline.

Khi checkpoint thất bại giữa chừng, chỉ bỏ hoặc hoàn tác phần thay đổi của chính
checkpoint theo quyết định của human; không dùng thao tác Git phá hủy và không
đụng tới thay đổi có sẵn của thành viên khác.

## 7. Kế hoạch checkpoint

### B1 — Backend acceptance readiness (P0)

Mục tiêu: bảo đảm Backend sẵn sàng cho hosted cloud-edge acceptance mà không cần
operator đoán trạng thái nội bộ.

Công việc:

- rà startup production fail-fast cho database, JWT secret, edge secret, CORS và
  `MOCK_FACTORY_ENABLED=false`;
- kiểm tra health/log hiện tại có đủ nhận biết revision, environment, database và
  runtime worker lifecycle mà không lộ secret;
- kiểm tra edge reconnect đăng ký lại authoritative fleet và không seed robot mock;
- kiểm tra Backend nhận độc lập telemetry/task state của ít nhất hai robot;
- kiểm tra command lease, ACK, result, timeout và retry không phụ thuộc UI;
- bổ sung regression test nhỏ nhất cho mọi lỗi phát hiện trong acceptance.

Acceptance:

- Backend khởi động production đúng cấu hình và fail đóng khi thiếu cấu hình bắt buộc;
- unauthenticated browser endpoint bị từ chối, edge secret không dùng được như JWT;
- hai robot không ghi đè state của nhau;
- reconnect/resync không tạo robot trùng hoặc làm sống lại sample cũ;
- command đạt đủ happy path và edge-offline negative path;
- log/evidence không chứa password, JWT secret hoặc edge secret.

Implementation result (2026-08-26): **Backend readiness complete**.

- Cloud Run `K_REVISION`, environment, persistence mode, telemetry source and
  active worker set are recorded in the startup log without secret values.
- Bridge reconnect preserves existing telemetry for the authoritative two-robot
  registry and does not emit a duplicate factory reset when membership is unchanged.
- The Backend integration regression covers bridge registration, independent
  telemetry ordering for two robots, stale-sample rejection and ROS task-state fan-out.
- API tests are isolated from a developer `.env`; PostgreSQL-gated tests continue
  to opt in through `TEST_DATABASE_URL` instead of accidentally using runtime data.
- Targeted B1 verification: 143 tests passed.
- Complete Backend test suite: 338 tests passed.
- Ruff lint and format check passed; canonical workspace Mypy passed 91 source files.

This result closes Backend code readiness only. The hosted GCE two-AMR run and
network evidence remain the acceptance gate after B2 instrumentation.

### B2 — Latency, drop và runtime evidence (P0)

Mục tiêu: cung cấp số đo cần thiết cho tiêu chí nâng cao của nhóm.

Công việc:

- giữ riêng `source_timestamp`, Backend ingest timestamp và broadcast timestamp;
- đo ROS-to-Backend latency tại ingress;
- cho phép frontend suy ra Backend-to-browser latency từ event timestamp mà không
  thay đổi công thức KPI nghiệp vụ;
- theo dõi accepted, stale/rejected, persisted và broadcast telemetry counts;
- ghi nhận queue overflow hoặc dropped/coalesced update nếu có;
- xuất số liệu qua health/log/metric contract tối thiểu đã được thống nhất, không
  đưa hệ thống metrics mới vào khi chưa cần.

Acceptance:

- có thể ghi p50/p95 latency cho một hosted run;
- có accepted/rejected/dropped counts giải thích được;
- instrumentation không làm đổi thứ tự telemetry hoặc block ingestion;
- timestamp validation và robot isolation có regression test.

Implementation result (2026-08-26): **Backend instrumentation complete**.

- `robot.telemetry.data` remains the Phase 1 `RobotTelemetry` payload; an optional
  envelope `meta` adds source, Backend ingest and broadcast UTC timestamps.
- The machine-authenticated `GET /internal/v1/runtime-evidence` endpoint reports
  accepted, stale and service-level rejection counts plus bounded p50/p95
  source-to-ingest latency.
- Persistence evidence distinguishes submitted, coalesced, pending, persisted and
  failed samples. WebSocket evidence distinguishes broadcast events, delivery
  attempts, successful deliveries and failed client deliveries.
- Latency uses a bounded 10,000-sample process-local window. Counters reset with
  the Cloud Run process and must be recorded together with its `K_REVISION`.
- Targeted B2 verification: 33 tests passed.
- Complete Backend test suite: 341 tests passed.
- Ruff lint and format check passed; canonical workspace Mypy passed 93 source files.

This result makes hosted measurement possible; it does not claim production
latency or drop-rate values until the GCE two-AMR acceptance run records them.

### B3 — Read-only operational history (P1)

Mục tiêu: dùng dữ liệu đã persist để điều tra và chứng minh acceptance, không xây
full incident replay UI.

Candidate API, chỉ triển khai phần thực sự cần cho acceptance:

- telemetry history theo `robot_id` và khoảng thời gian;
- task transition history;
- bridge health history;
- alert occurrence/history;
- KPI snapshot history;
- business audit query dành cho `MONITOR`.

Yêu cầu:

- bắt buộc time-range và pagination/limit có giới hạn;
- dùng index/partition hiện có, không load history không giới hạn vào RAM;
- kiểm tra role tại Backend;
- response không trả password hash, credential hoặc secret;
- mục tiêu p95 truy vấn telemetry 24 giờ của một robot dưới 500 ms trên dữ liệu
  capacity test đã thống nhất.

Acceptance:

- truy vấn đúng robot/time range và có ordering ổn định;
- input timezone/range/limit sai bị từ chối;
- Designer không đọc business audit nếu contract vẫn giới hạn cho Monitor;
- query plan/capacity evidence được ghi lại trước khi mở rộng retention.

Implementation result (2026-08-26): **Minimum acceptance API complete**.

- `GET /api/v1/robots/{robot_id}/telemetry-history` provides read-only,
  newest-first telemetry using a required UTC range, exclusive `before` cursor
  and a bounded 1–500 result limit. PostgreSQL filters on `robot_id` and the
  partition key `source_timestamp`.
- `GET /api/v1/audit-events` provides a bounded time range, composite
  `(before, before_id)` cursor, optional resource filters and stable
  `created_at DESC, id DESC` ordering.
- Existing read roles may inspect robot telemetry history; business audit remains
  restricted to `MONITOR` by the Backend authorization boundary.
- Task, bridge, alert and KPI history remain durable but do not receive new APIs
  in this checkpoint. Current-state endpoints already cover the MVP UI and full
  replay remains out of scope.
- Targeted B3 verification: 74 tests passed.
- Complete Backend test suite: 350 tests passed.
- Ruff lint and format check passed; canonical workspace Mypy passed 95 source files.

Cloud SQL query-plan and p95 capacity evidence remain a hosted operational gate;
retention must not be expanded based only on the local correctness tests.

### B4 — Apply capability and failure clarity (P1)

Mục tiêu: Backend không tuyên bố áp dụng thành công một layout mà ROS edge không
hỗ trợ.

Công việc trong Backend:

- giữ immutable `layout_id` và `layout_version` trong command payload;
- truyền route/layout identity và dữ liệu cần thiết theo contract đã thống nhất;
- validate phần Backend có thẩm quyền trước khi tạo command;
- bảo toàn failure reason từ edge ở mức an toàn để Monitor điều tra;
- scenario chỉ chuyển `APPLIED` sau positive execution result;
- retry idempotent, có budget và không làm mất attempt history.

Phần topology adapter, route execution và collision avoidance thuộc ROS edge,
không được triển khai lẫn trong `apps/backend`.

Acceptance:

- unsupported layout tạo kết quả thất bại rõ ràng, không chuyển `APPLIED`;
- duplicate ACK/result không làm sai lifecycle;
- late result của attempt cũ không hoàn tất attempt mới;
- restart Backend không làm mất durable command history.

Implementation result (2026-08-26): **Backend command lifecycle complete**.

- Edge commands preserve the scenario's immutable `layout_id`, `layout_version`
  and `route_id`; Backend validation and approval complete before command creation.
- ACK and result idempotency is scoped to the exact operation, attempt and bridge.
  Exact duplicate delivery has no repeated audit, WebSocket or apply side effect.
- A terminal or timed-out old attempt cannot mutate the active retry. Retry remains
  bounded by `max_retries` and appends rather than replacing attempt history.
- Edge failure detail remains bounded by the request schema and is retained on the
  failed attempt; a failed result leaves the scenario `APPROVED`.
- PostgreSQL command and attempt tables remain the durable source across Backend
  restarts. The in-memory repository is test/development state and is not durable.
- ROS topology support, route execution and collision avoidance remain explicitly
  outside Backend authority and must return a positive result before `APPLIED`.

### B5 — Production hardening có điều kiện (P2)

Chỉ bắt đầu khi B1–B4 đã hoàn thành và có nhu cầu đo được:

- per-bridge identity và ownership khi có nhiều trusted bridge;
- overlapping secret rotation;
- batch ingestion và request-size limit;
- explicit telemetry backpressure;
- restore/resync snapshot sau process restart;
- durable outbox/single command worker;
- shared pub/sub hoặc distributed coordination trước khi tăng hơn một instance;
- backup/restore và retention-job observability.

Không xây các mục này chỉ vì khả năng mở rộng trong tương lai.

## 8. Thứ tự thực hiện

```text
B1 acceptance readiness
  → B2 latency/drop evidence
  → hosted two-AMR acceptance
  → sửa regression tìm thấy
  → B3 history API tối thiểu nếu acceptance cần
  → B4 apply failure clarity cùng contract ROS
  → B5 chỉ khi có nhu cầu production đo được
```

Hosted acceptance là cổng quyết định. Nếu B1/B2 đã đủ và run thành công, không
được trì hoãn MVP chỉ để xây thêm B3–B5.

## 9. Testing và Definition of Done

Mỗi checkpoint Backend phải:

- giữ schema và status code tương thích với contract đã chốt;
- có test tập trung cho logic không tầm thường và regression test cho bug;
- chạy Ruff, format check, Mypy và pytest Backend phù hợp;
- không hạ quality gate để đạt CI xanh;
- cập nhật tài liệu trong `apps/backend` phản ánh đúng code thực tế;
- ghi rõ test nào bị skip vì thiếu PostgreSQL/hosted environment;
- phân biệt component verification với hosted acceptance evidence;
- không đưa credential hoặc production data vào fixture/log.

Checkpoint chỉ hoàn thành khi code, test, tài liệu và CI/build liên quan cùng đạt.

## 10. Ngoài phạm vi

- AI/ML hoặc continuous optimizer;
- predictive maintenance;
- MES/ERP integration;
- CAD/BIM toàn nhà máy;
- điều khiển robot thật;
- collision physics nâng cao;
- full incident replay UI;
- Admin role hoặc user-management product API;
- multi-region hoặc multi-instance architecture khi chưa có nhu cầu;
- thay đổi frontend, ROS, SimPy, `twin-core` hoặc migration trong nhánh này.

## 11. Điều kiện bàn giao giai đoạn Backend

Backend được coi là sẵn sàng bàn giao khi nhóm có thể chứng minh:

1. Hai AMR Gazebo gửi telemetry và task lifecycle độc lập qua Backend.
2. Browser nhận snapshot và realtime event dùng cùng contract với mock.
3. KPI, alert và runtime health phản ánh dữ liệu ROS thay vì mock seed.
4. Designer không thể approve/apply; Monitor không thể chạy scenario Designer.
5. Apply tạo durable command và chỉ hoàn tất sau ROS result thành công.
6. Edge offline tạo timeout/disconnect alert; retry tạo attempt mới có kiểm soát.
7. State bền vững cần thiết tồn tại sau Backend restart.
8. Latency và dropped-update evidence được ghi với commit/revision tương ứng.
9. Backend checks, container check và hosted acceptance liên quan đều đạt.

Mọi thay đổi sau hợp đồng này phải bám checkpoint nhỏ nhất đủ đạt mục tiêu, dừng
sau mỗi checkpoint để nhóm review và commit trước khi bắt đầu phần tiếp theo.
