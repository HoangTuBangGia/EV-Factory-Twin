## UX audit — kết luận

Vấn đề gốc không phải visual UI mà là app đang tổ chức theo technical objects (`layout`, `version`, `scenario`, `command`) thay vì theo mục tiêu của hai role. Một user mới không biết bước tiếp theo là gì, tại sao có quyền/không có quyền, hay hành động của họ tác động tới factory khi nào.

Audit này dựa trên flow hiện có trong frontend/API và đã được đối chiếu với code; chưa thay thế usability test với user thật.

## Ràng buộc kỹ thuật đã xác minh

Các ràng buộc dưới đây quyết định phạm vi thật của từng đề xuất. Chúng được đọc trực tiếp từ code, không suy đoán.

| # | Ràng buộc | Bằng chứng | Hệ quả cho UX |
|---|---|---|---|
| C1 | "Candidate" không tồn tại như một entity. Layout version và scenario là hai object rời; workflow status chỉ nằm ở scenario, layout version không có status. | `apps/frontend/src/schemas/layout.ts`, `apps/frontend/src/schemas/scenario.ts` | Mọi UI nói "candidate" phải là **view model dẫn xuất** ở frontend, join `scenario.config.layout_id + layout_version` với layout version đang mở. Không cần đổi backend. |
| C2 | Apply là hai pha. `POST /apply` chỉ tạo command `PENDING`; factory runtime chỉ reset khi bridge trả `COMPLETED`. | `command_service.py:487-503`, `command_service.py:536-552`, `scenario_service.py:267-269`, `mock_factory.py:165-180` | Copy xác nhận apply không được nói "ngay bây giờ". Timeline phải có pha bridge. |
| C3 | `REJECTED` là trạng thái cuối. Transition được hard-code từng cặp: `SIMULATED→SUBMITTED`, `SUBMITTED→{APPROVED,REJECTED}`, `APPROVED→APPLIED`. | `scenario_repository.py:504-514` | Designer bị reject **không thể sửa và submit lại**; phải chạy scenario mới. Đây là bug workflow, không phải vấn đề copy. |
| C4 | Không có cột nào để lưu lý do review. | `supabase/migrations/20260814000200_create_scenarios_and_audit.sql` | Reject reason cần migration + đổi contract, không phải chỉ thêm textarea. |
| C5 | `congestion_percent` là một số tổng hợp duy nhất, không có attribution theo zone. | `packages/twin-core/src/twin_core/metrics/authoritative.py:84` | Không thể hiển thị "congestion +4% near warehouse door" mà không đổi KPI contract. |
| C6 | Backend cho cả hai role đọc layout (`READ_ROLES`), nhưng frontend gate bằng `layout:edit` (Designer-only). | `apps/backend/src/ev_twin_api/api/layouts.py:35,56,106`, `apps/frontend/src/lib/auth/permissions.ts` | Compare map cho Monitor chỉ cần thêm permission ở **frontend**, backend đã sẵn sàng. |
| C7 | Creator không được review hoặc apply scenario của chính mình; chỉ creator được submit. | `scenario_repository.py:381-388` | Separation of duties đã được backend enforce. UI chỉ cần giải thích, không cần tự kiểm tra. |
| C8 | `GET /api/v1/scenarios` trả toàn bộ, không filter, không pagination. Baseline là object synthetic (`id="baseline"`, `created_by=null`) và **không** nằm trong list. | `apps/backend/src/ev_twin_api/api/scenarios.py:53-59`, `scenario_service.py:162-176` | Review queue filter được ở client. Ceiling: list dài dần theo thời gian. |
| C9 | Không có design system component. Không có `components/ui/`, toàn bộ style là ~105 dòng class tay trong một file. | `apps/frontend/src/app/globals.css` | Mỗi UI mới đều phải viết CSS tay. Không cản trở, nhưng cộng effort. |
| C10 | Label button đang bị assert cứng trong e2e và unit test. | `apps/frontend/e2e/hosted-rbac.spec.ts:67,71,76,86,94`, `scenario-actions.test.tsx:28,56` | Đổi copy là đổi cả test. E2e `openScenario` yêu cầu tab candidate `toHaveCount(1)`, nên **không được** đặt default filter làm ẩn candidate. |

## Journey 1 — Designer

Mục tiêu: tạo một phương án logistics tốt hơn và gửi Monitor duyệt.

```text
Login
  → Overview
  → Layouts
  → chọn/tạo layout
  → chỉnh stations/routes/zones/config
  → Create new version        (tạo layout version immutable)
  → Simulate this version
  → nhập cấu hình scenario
  → Run benchmark             (tạo scenario, status = SIMULATED)
  → đọc KPI
  → Submit for review
  → chờ Monitor
```

Lưu ý theo C1: hai bước in đậm tạo ra **hai object khác nhau**. User nghĩ mình đang làm một việc.

### Friction của Designer

| Mức độ | Điểm vướng | Tác động |
|---|---|---|
| Critical | Không có “next best action” xuyên suốt flow | User không biết sau khi tạo layout phải sang đâu, hoặc sau benchmark cần submit. |
| Critical | Bị reject là bế tắc (C3) | Không có đường sửa và submit lại. User phải tự suy ra rằng phải chạy scenario mới từ đầu. |
| Critical | Route drawing yêu cầu hiểu thứ tự start station → waypoint → end station | Dễ thao tác sai; thông báo hướng dẫn tạm thời, không có guided interaction bền vững. |
| High | “Create new version” là khái niệm kỹ thuật | User không hiểu đây là lưu bản nháp, ghi đè hay thay đổi factory live. |
| High | Zones chỉnh bằng JSON | Không phù hợp user nghiệp vụ; lỗi cú pháp làm mất preview và gây sợ thao tác. |
| High | Scenario form có quá nhiều tham số kỹ thuật cùng lúc | `travel_time`, `loading_time`, `simulation_time`, arrival interval… không được chia thành basic/advanced. |
| Medium | Scenario history là danh sách ID/trạng thái | Khó tìm candidate cần xử lý, không biết candidate nào là mới nhất/của mình/chờ duyệt. |
| Medium | Layout, simulation và KPI nằm ở màn khác nhau | User phải tự ghép quan hệ giữa thay đổi layout và kết quả KPI (C1). |

## Journey 2 — Monitor

Mục tiêu: đánh giá một đề xuất, quyết định áp dụng an toàn, theo dõi kết quả.

```text
Login
  → Overview / Scenarios
  → tìm scenario SUBMITTED
  → đọc configuration + KPI baseline comparison
  → Approve hoặc Reject
  → Apply to factory          (chỉ tạo command PENDING)
  → chờ bridge acknowledge + complete
  → quay lại Factory để xác nhận runtime
```

### Friction của Monitor

| Mức độ | Điểm vướng | Tác động |
|---|---|---|
| Critical | Không có inbox “Needs my review” | Monitor phải tự tìm scenario `SUBMITTED` trong lịch sử. |
| Critical | Apply là hành động có ảnh hưởng lớn nhưng tác động bị phân tán | Apply reset AMR, task, alert, metric (C2); thông tin đó không nằm ngay tại decision/action theo cách đủ nổi bật. |
| High | Không có màn compare layout trước/sau cho Monitor | KPI có nhưng thiếu bối cảnh vật lý của thay đổi. |
| High | Approve và Apply là hai bước tách rời nhưng không có timeline rõ | Dễ approve rồi không biết cần apply tiếp, hoặc không biết apply đã thành công chưa — nhất là vì apply là hai pha (C2). |
| High | Command history thiên về kỹ thuật | `operation_id`, lease, bridge, attempts hữu ích cho support engineer hơn Monitor. |
| Medium | Không có reject reason / request revision rõ ràng | Designer không có feedback có cấu trúc để sửa candidate (và theo C3 thì cũng không có đường sửa). |
| Medium | Navigation mang tính module | Overview, Factory, Scenarios, Commands không phản ánh “việc tôi cần làm hôm nay”. |

## Wireframe tối thiểu đề xuất

Không cần redesign toàn bộ hay thêm framework. Không tạo route mới: đưa guidance vào frame và nâng cấp hai page đã có.

### Next action strip (cả hai role)

Một dải role-aware nằm trong application frame, hiện trên mọi page kể cả Overview cockpit.

```text
┌──────────────────────────────────────────────────────────┐
│ NEXT STEP · Battery flow v4 simulated but not submitted   │
│ Monitor review is required before it can reach the factory│
│                                        [Review candidate] │
└──────────────────────────────────────────────────────────┘
```

Đây là thứ trực tiếp trả lời “bước tiếp theo là gì?” và là inbox pointer cho Monitor. Filter ở page Scenarios là drill-down, không phải điểm phát hiện.

### Designer — page Layouts

```text
┌──────────────────────────────────────────────────────────┐
│ Step 1 Layout  →  Step 2 Simulate  →  Step 3 Submit       │
├───────────────────────────────┬──────────────────────────┤
│ Candidate geometry            │ LIVE MAP PREVIEW         │
│ stations / routes / config    │    drag/click map        │
├───────────────────────────────┴──────────────────────────┤
│ Drawing BATTERY_DELIVERY:                                 │
│ [1 Select start] → [2 Add waypoints] → [3 Select end]    │
├──────────────────────────────────────────────────────────┤
│ Saving creates an immutable revision. The live factory    │
│ does not change until a Monitor applies it.               │
│                            [Save candidate revision]      │
└──────────────────────────────────────────────────────────┘
```

- `Save candidate revision` thay cho `Create new version`, kèm câu giải thích live factory chưa đổi.
- Khi user đang vẽ route, hiện stepper có state thật thay vì một dòng notice tạm.
- Zones vẫn là JSON trong checkpoint này; chuyển sang form UI ở P1.

### Monitor — page Scenarios

```text
┌──────────────────────────────────────────────────────────┐
│ [All] [Awaiting review 2] [My candidates] [Approved] [Applied]
├───────────────┬──────────────────────────────────────────┤
│ Candidate list│ Candidate: e2e-rbac-1724...               │
│               │                                           │
│               │ Simulated ─ Submitted ─● Approved ─ Applied│
│               │                                           │
│               │ KPI vs baseline (bảng so sánh đã có)      │
│               │                                           │
│               │ [Reject]  [Approve]                       │
└───────────────┴──────────────────────────────────────────┘
```

Sau approve, apply confirmation phải nói đúng theo C2:

```text
Apply "candidate-01" to the factory?
A command is queued for the Fleet Manager bridge. When the bridge
completes it, factory runtime resets AMRs, tasks, alerts and metrics.
[Cancel] [OK]
```

Sau apply, timeline hiển thị đúng hai pha:

```text
Approved → Apply queued → Bridge acknowledged → Applied
```

`Commands` vẫn tồn tại nhưng trở thành trang chẩn đoán/support, không phải nơi Monitor phải vào để hiểu kết quả apply.

Không đưa risk theo zone (`congestion +4% near warehouse door`) vào wireframe này: theo C5 nó không sản xuất được mà không đổi KPI contract, và đổi KPI contract đã bị loại khỏi scope.

## Scope implementation nên chốt

### P0 — làm trước, phạm vi nhỏ nhưng tác động lớn

Frontend-only. Không đổi backend contract, database schema hoặc phân quyền.

1. **Candidate view model** (`lib/workflow.ts`, pure functions). Join scenario ↔ layout version theo C1, phân loại queue, và suy ra next action theo role. Đây là phần logic thật của P0, không phải phần layout UI.
2. **Next action strip** role-aware trong application frame, link sang queue tương ứng bằng query param.
3. **Workflow timeline** dùng trạng thái đã có: `SIMULATED → SUBMITTED → APPROVED → APPLIED`, cộng nhánh `REJECTED`, cộng pha command (`PENDING → ACKNOWLEDGED → COMPLETED`) theo C2.
4. **Đổi nhãn/copy** để loại bớt thuật ngữ kỹ thuật: `Create new version` → `Save candidate revision`, kèm giải thích layout live chưa đổi. Cập nhật test theo C10.
5. **Contextual guidance cho route drawing**: stepper 3 bước có state.
6. **Apply confirmation** nêu rõ reset runtime **và** rằng nó xảy ra khi bridge hoàn tất (C2). Confirm đã tồn tại — đây là reword, không phải feature mới.
7. **Queue filter** ở scenario history: `All`, `Awaiting review`, `My candidates`, `Approved`, `Applied`. Default là `All` để không vi phạm C10; strip là điểm phát hiện, filter là drill-down.

### P1 — sau khi P0 được user test

1. Compare map current/candidate cho Monitor. Cần thêm `layout:view` vào bảng permission frontend (C6); backend không đổi.
2. Form UI cho no-go/congestion zones, bỏ JSON khỏi happy path. Map editor đã có abstraction `FactoryPlantMapEditor` để mở rộng.
3. Basic vs Advanced scenario settings.
4. Gom command status vào candidate timeline (đưa `Commands` về vai trò chẩn đoán).
5. Quyết định vị trí của `OptimizationPanel` — hiện đang nằm cuối page Scenarios và chưa có chỗ trong wireframe mới.

### P2 — checkpoint backend riêng, không phải UX copy

Reject/request-revision có cấu trúc. Theo C3 và C4 việc này gồm:

- migration thêm cột review note vào `public.scenarios`
- transition SQL mới cho đường quay lại (`REJECTED → SIMULATED` hoặc status `REVISION_REQUESTED`)
- đổi `scenario_service` + response schema + api-client + Zod schema

Ưu tiên độc lập với UX vì "Designer bị reject là bế tắc" là bug workflow, không phải vấn đề trình bày.

### Không làm trong checkpoint UX đầu tiên

- CAD editor hoàn chỉnh.
- Drag polygon phức tạp.
- Thay đổi authoritative KPI/SimPy/ROS flow — kể cả để có risk theo zone (C5).
- Thay schema layout/version hiện tại.
- Tái kiến trúc frontend lớn chỉ để đổi UI.
- Route mới cho workspace: guidance đi vào frame và page đã có.

## Tiến độ implementation

Cập nhật 28/08/2026. P0 đã commit trên branch `feat/frontend-data-driven-layout-editor` ở
`22c43ab`; phần wire `candidateForLayoutVersion` vào page Layouts và toàn bộ P1 item 1 vẫn chưa
commit. Chi tiết checkpoint: `docs/changes/workflow-guidance-p0.md`,
`docs/changes/layout-comparison-p1.md`.

| # | Item P0 | Trạng thái | Nơi implement |
|---|---|---|---|
| 1 | Candidate view model | Xong | `lib/workflow.ts` — `stageState`, `applyProgress`, `filterQueue`, `newestFirst`, `nextAction`, `candidateForLayoutVersion`. Join theo C1 được `VersionCandidate` trong `app/layouts/page.tsx` dùng để nói version đang mở đứng ở đâu trong review. |
| 2 | Next action strip | Xong | `components/workflow/next-action-strip.tsx`, mount trong `application-frame.tsx`; biến thể `.floating` cho Overview cockpit, ẩn dưới 1200px. |
| 3 | Workflow timeline | Xong | `components/workflow/workflow-timeline.tsx`, gắn vào chi tiết candidate ở `app/scenarios/page.tsx`. Pha bridge đọc `acknowledged_at` từ attempts nên command đã fail vẫn cho thấy đi được tới đâu. |
| 4 | Đổi nhãn/copy | Xong | `app/layouts/page.tsx`: `Save candidate revision` + dòng giải thích live factory chưa đổi. Không test nào assert nhãn cũ nên C10 không phát sinh sửa test. |
| 5 | Route drawing stepper | Xong | `RouteStepper` trong `app/layouts/page.tsx`, state thật theo số waypoint đã đặt. |
| 6 | Apply confirmation | Xong | Reword confirm trong `app/scenarios/page.tsx` theo đúng hai pha của C2. |
| 7 | Queue filter | Xong | Chip đọc/ghi `?queue=`, default `all`, đặt ngoài `.scenario-tabs` để không phá `toHaveCount(1)` của e2e (C10). |

Phát sinh ngoài 7 item, cần thiết để làm được chúng:

- `scenarios` chuyển vào Zustand store (`setScenarios` / `updateScenario`) để strip ở frame và
  page Scenarios dùng chung một list; `upsertScenario` cục bộ của page bị xoá.
- Fixture dùng chung `fixtureScenario` / `fixtureApplyCommand` cho hai file test mới.
- CSS viết tay theo C9: `.workflow-strip`, `.workflow-timeline`, `.workflow-stages`,
  `.workflow-phases`, `.queue-filters`, `.route-stepper`.

Quality gate 28/08/2026, chạy trong `apps/frontend`: `npm run lint` pass, `npm run typecheck`
pass, `npm test` 32 file / 139 test pass (mới: 20 unit workflow + 7 component + 2 test Layouts
cho candidate của version), `npm run build` pass 14/14 page. `npm run test:e2e` tự skip vì thiếu
credential hosted RBAC, phải xác nhận trên CI.

Còn nợ trong P0:

- Strip và page Scenarios gọi trùng `GET /scenarios`, cộng với fetch trùng sẵn có ở
  `hooks/use-applied-factory-layout.ts`. Gộp thành một đường hydrate là checkpoint riêng.
  Page Layouts **không** fetch thêm: nó đọc `scenarios` từ store do strip ở frame nạp.
- C3 vẫn nguyên: reject vẫn là bế tắc, hiện chỉ được **giải thích** bằng copy. Đúng scope, việc
  sửa thuộc P2.

### P1

| # | Item | Trạng thái | Ghi chú |
|---|---|---|---|
| 1 | Compare map current/candidate cho Monitor | Xong | `layout:view` thêm vào bảng permission frontend cho cả hai role, backend không đổi (C6). Diff hình học tách thành hàm thuần `lib/layout-diff.ts`; panel là `<details>` nên chưa mở thì không fetch. Chi tiết: `docs/changes/layout-comparison-p1.md`. |
| 2 | Form UI cho no-go/congestion zones | Xong | JSON đã được thay bằng form; click map để vẽ polygon, sửa metadata/toạ độ và preview cả hai loại zone. Chi tiết: `docs/changes/layout-zone-editor-p1.md`. |
| 3 | Basic vs Advanced scenario settings | Xong | Form cơ bản dùng layout defaults, assumptions chuyên sâu nằm trong disclosure; có live summary và reset. Chi tiết: `docs/changes/scenario-settings-p1.md`. |
| 4 | Gom command status vào candidate timeline | Xong | Scenarios hydrate command bền vững, chọn operation mới nhất theo candidate và đưa lifecycle/detail/link chẩn đoán vào timeline. Chi tiết: `docs/changes/candidate-command-timeline-p1.md`. |
| 5 | Vị trí của `OptimizationPanel` | Chưa bắt đầu | |

Quality gate sau P1 item 1, chạy trong `apps/frontend`: `npm run lint` pass, `npm run typecheck`
pass, `npm test` 34 file / 151 test pass (mới: 6 unit `layout-diff` + 5 component
`layout-comparison` + 1 test permission), `npm run build` pass 14/14 page.

Quality gate sau P1 item 2, chạy trong `apps/frontend`: `npm run lint` pass, `npm run typecheck`
pass, targeted Layouts 10/10 test pass, full `npm test -- --run` 34 file / 154 test pass,
`npm run build` pass 14/14 page.

Quality gate sau P1 item 3, chạy trong `apps/frontend`: `npm run lint` pass, `npm run typecheck`
pass, targeted form 4/4 test pass, full `npm test -- --run` 35 file / 158 test pass,
Playwright list nhận 3 test (2 hosted test skip do thiếu credential), `npm run build` pass 14/14 page.

Quality gate sau P1 item 4, chạy trong `apps/frontend`: `npm run lint` pass, `npm run typecheck`
pass, targeted workflow/timeline/Scenarios 30/30 test pass, full `npm test -- --run` 36 file /
161 test pass, Playwright list nhận 3 test (2 hosted test skip do thiếu credential),
`npm run build` pass 14/14 page.

Còn nợ trong P1 item 1: khi không có candidate nào APPLIED thì không có mốc so sánh, panel nói
thẳng điều đó chứ không dựng baseline giả. Congestion vẫn là một số tổng (C5) nên change list chỉ
báo được zone bị đổi hình, không quy được delay cho zone.

P2: chưa bắt đầu.

## Tiêu chí thành công

Test với ít nhất 3 Designer và 3 Monitor đại diện. Mỗi người phải hoàn thành các task sau không cần hướng dẫn trực tiếp:

- Designer: tạo candidate, sửa route, chạy simulation và submit.
- Monitor: tìm candidate chờ review, hiểu rủi ro, approve/apply và xác nhận trạng thái.

Đo: tỷ lệ hoàn thành, thời gian, số lần hỏi trợ giúp, và điểm user dừng lại. Nếu người dùng vẫn không nói được “bước tiếp theo là gì?” sau mỗi màn chính, UX chưa đạt.

Checkpoint implementation đầu tiên: **P0 workflow guidance và role-aware queue**, không động tới backend contract.
