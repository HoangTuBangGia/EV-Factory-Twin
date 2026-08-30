# Improve UX Foundation

## Summary

Bổ sung lớp UX infrastructure còn thiếu sau khi P0-P2 workflow guidance đã hoàn thành. Tập trung vào feedback loops, connection resilience, onboarding, và operational controls — những pattern mà user mong đợi ở phần mềm vận hành nhưng chưa có trong codebase. Không trùng lặp với fixUX.md (workflow guidance, candidate view model, queue filter, timeline, copy rewording).

## Motivation

Audit UX độc lập (29/08/2026) xác nhận: domain UX tốt (NextActionStrip, role-aware nav, empty states, demo accounts), nhưng foundation UX thiếu nghiêm trọng. User mới không biết bắt đầu từ đâu, action thành công/thất bại không có feedback rõ ràng, WebSocket disconnect im lặng, không thể pause live view để inspect, alert stream không quản lý được. Những vấn đề này tồn tại bất kể workflow guidance tốt thế nào.

fixUX.md đã giải quyết "bước tiếp theo là gì?" và "candidate đang ở đâu?". Document này giải quyết "hành động của tôi có tác dụng không?", "dữ liệu còn tươi không?", "tôi đang nhìn cái gì?", và "làm sao dừng lại để xem kỹ?".

## Ràng buộc kỹ thuật

| # | Ràng buộc | Bằng chứng | Hệ quả |
|---|---|---|---|
| U1 | Không có component library (shadcn/Radix). Toàn bộ UI là custom CSS trong `globals.css` (~116 dòng). | `apps/frontend/src/app/globals.css` | Mọi component mới viết tay bằng Tailwind utility + CSS class. Không thêm dependency UI trừ khi được approve riêng. |
| U2 | Không có localStorage usage nào trong codebase. | grep toàn bộ `src/` | Onboarding persistence cần introduce pattern mới. Dùng `localStorage` với key prefix `ft-`. |
| U3 | Design tokens là CSS custom properties (`--bg`, `--panel`, `--cyan`, `--red`, etc.). Dark-theme only. | `globals.css:3-14` | Component mới phải dùng biến CSS, không hardcode màu. |
| U4 | Zustand store là single source of truth cho realtime data. ConnectionStatus đã có type `"CONNECTING" \| "LIVE" \| "OFFLINE" \| "MOCK"`. | `stores/factory-store.ts:9` | Banner/connection UI đọc từ store, không tạo state riêng. |
| U5 | ARIA patterns hiện có: `role="alert"` cho error, `role="status"` cho info, `aria-live="polite"` ở một chỗ. Không focus trap, không skip-nav. | Audit accessibility 29/08 | Toast/banner/dialog mới phải tuân thủ pattern này. Dialog cần focus trap. |
| U6 | E2E tests assert label text cụ thể (C10 trong fixUX.md). | `e2e/hosted-rbac.spec.ts` | Đổi/add text phải check e2e impact. |
| U7 | `window.confirm()` dùng ở 2 chỗ: layouts archive, scenario apply. | `layouts/page.tsx:505`, `scenarios/page.tsx:336` | Confirmation dialog thay thế cần cover cả hai case + giữ accessible. |

## Checkpoints

### CP1 — Toast Notification System [Priority: CRITICAL]

**Vấn đề:** Không có feedback sau action. Approve/submit/save thành công chỉ hiện inline text dễ trôi. User không biết action có tác dụng.

**Scope:**
- Tạo `components/ui/toast.tsx` và transient Zustand store helpers. Pure CSS animation, không thêm dependency.
- Toast types: `success`, `error`, `info`. Auto-dismiss 4s (success/info), manual dismiss (error).
- Position: bottom-right, stackable, max 3 visible.
- Accessibility: `role="status"` cho success/info, `role="alert"` cho error. `aria-live="polite"`.
- Tích hợp vào các action hiện có:
  - Scenario run complete → toast success với KPI summary
  - Scenario submit/approve/reject/request-revision → toast success
  - Layout save candidate revision → toast success
  - Apply command queued → toast info (không phải success, vì chưa applied)
  - Bất kỳ API error → toast error với message từ backend
- CSS: `.toast-container`, `.toast`, `.toast-success`, `.toast-error`, `.toast-info` trong `globals.css`. Dùng `--cyan`, `--red`, `--amber`.

**Không làm:**
- Toast queue persistence (mất khi refresh = đúng)
- Undo từ toast
- Rich content/actions trong toast

**Verification:**
- Unit test: `toast.test.tsx` — render, auto-dismiss, manual dismiss, stacking, aria attributes
- Manual: mỗi action listed trên phải hiện toast đúng type
- `npm run lint && npm run typecheck && npm test -- --run && npm run build`

**Effort estimate:** 4-6h

---

### CP2 — WebSocket Offline Banner + Reconnect [Priority: CRITICAL]

**Vấn đề:** WebSocket disconnect chỉ hiện badge nhỏ ở sidebar/topbar. User không biết dữ liệu stale, không có nút reconnect. Operations tool mà silent stale = nguy hiểm.

**Scope:**
- Tạo `components/layout/connection-banner.tsx`: persistent banner khi `connectionStatus === "OFFLINE"`.
- Nội dung: "Live data disconnected. Displayed data may be stale." + nút "Reconnect".
- Position: fixed top, dưới topbar, trên page content. Full-width, `--amber` accent.
- Reconnect button gọi lại logic reconnect đã có trong `use-factory-socket.ts` (expose `reconnect()` method nếu chưa có).
- Transition: `CONNECTING` → banner đổi sang "Reconnecting..." với spinner, disable nút.
- `LIVE` → banner slide-out.
- Accessibility: `role="alert"`, `aria-live="assertive"` khi chuyển OFFLINE.
- Mount trong `application-frame.tsx`, giữa Topbar và children.

**Không làm:**
- Banner cho `MOCK` mode (đã có indicator khác)
- Auto-retry config UI (logic reconnect tự động đã đủ)
- Sound notification

**Verification:**
- Unit test: `connection-banner.test.tsx` — render per status, reconnect click, aria
- Manual: tắt backend → banner hiện → bật lại → reconnect thành công → banner ẩn
- `npm run lint && npm run typecheck && npm test -- --run && npm run build`

**Effort estimate:** 2-3h

---

### CP3 — First-Login Onboarding Tour [Priority: HIGH]

**Vấn đề:** User mới không biết bắt đầu từ đâu. NextActionStrip giúp nhưng giả định user đã hiểu domain model.

**Scope:**
- Tạo `components/onboarding/onboarding-tour.tsx`: modal-based tour 4 bước.
- Steps:
  1. "Welcome to EV Factory Digital Twin" — giới thiệu ngắn mục tiêu platform
  2. "Your role: {DESIGNER|MONITOR}" — giải thích trách nhiệm, link đến page chính
  3. "The cockpit" — giải thích overview panels (KPI, alerts, fleet, map)
  4. "Your first task" — hướng dẫn đến NextActionStrip, giải thích workflow cơ bản
- Persistence: `localStorage.setItem("ft-onboarding-done:<user-id>", "1")` để Designer và Monitor dùng chung browser không che tour của nhau.
- Skip button trên mỗi step. "Don't show again" checkbox.
- Role-aware content: step 2-4 khác nhau cho DESIGNER vs MONITOR.
- Styling: modal overlay dùng CSS, không dialog element (focus trap thủ công bằng useEffect).
- Accessibility: focus trap, Escape đóng, `aria-modal="true"`, `role="dialog"`.

**Không làm:**
- Highlight/tour gắn vào DOM elements (quá phức tạp cho MVP)
- Multi-language
- Onboarding cho từng page riêng

**Verification:**
- Unit test: `onboarding-tour.test.tsx` — render steps, skip, persist, role content
- Manual: xóa localStorage → reload → tour hiện → complete → reload → không hiện lại
- `npm run lint && npm run typecheck && npm test -- --run && npm run build`

**Effort estimate:** 4-5h

---

### CP4 — Pause/Resume Live Updates [Priority: HIGH]

**Vấn đề:** Không thể đóng băng view để inspect, chụp màn hình, hoặc giảm cognitive load. WebSocket luôn active.

**Scope:**
- Thêm `paused: boolean` vào `factory-store.ts`. Default `false`.
- Toggle button trong topbar (và cockpit overlay): icon pause/play + label.
- Khi paused: `use-factory-socket.ts` vẫn nhận event nhưng không apply vào store. Buffer events.
- Khi resume: apply buffered events, clear buffer.
- Visual indicator: topbar/show trạng thái "PAUSED" với `--amber` accent khi paused.
- Buffer limit: nếu > 500 events trong khi paused, drop oldest + hiện warning toast (CP1).
- Persist pause state: KHÔNG persist. Refresh = resume. Đúng cho operations tool.

**Không làm:**
- Time-travel / replay from buffer
- Selective pause (chỉ robots, chỉ metrics)
- Keyboard shortcut (có thể thêm sau)

**Verification:**
- Unit test: `factory-store.test.ts` — pause/resume/buffer/drop logic
- Manual: pause → robots đứng yên → resume → catch up
- `npm run lint && npm run typecheck && npm test -- --run && npm run build`

**Effort estimate:** 3-4h

---

### CP5 — Simulation Progress Feedback [Priority: MEDIUM-HIGH]

**Vấn đề:** Scenario run chỉ hiện "Running..." trên button. Không biết tiến triển hay treo.

**Scope:**
- Trong `scenario-run-form.tsx` hoặc nơi trigger run: khi running, hiện elapsed timer (`0:00`, `0:05`, ...) bên cạnh button.
- Indeterminate progress bar (CSS animation) dưới form.
- Nếu backend trả về estimated duration trong tương lai, dùng nó. Hiện tại: chỉ elapsed time.
- Cancel button: backend hiện không có cancel endpoint; disable + tooltip "Cannot cancel mid-run".
- Timeout warning: nếu > 60s, hiện toast info "Simulation still running..." (dùng CP1).

**Không làm:**
- Server-side progress reporting (backend change, separate checkpoint)
- Estimated time remaining
- Background run + notification when done

**Verification:**
- Unit test: elapsed timer component
- Manual: run scenario → timer chạy → complete → timer ẩn
- `npm run lint && npm run typecheck && npm test -- --run && npm run build`

**Effort estimate:** 2-3h

---

### CP6 — Styled Confirmation Dialog [Priority: MEDIUM]

**Vấn đề:** `window.confirm()` phá visual design, không rich content, không accessible focus trap.

**Scope:**
- Tạo `components/ui/confirm-dialog.tsx`: reusable modal dialog.
- Props: `title`, `message` (ReactNode), `confirmLabel`, `cancelLabel`, `variant` ("danger" | "default"), `onConfirm`, `onCancel`, `open`.
- Focus trap, Escape đóng, click outside đóng.
- Replace 2 `window.confirm()` calls:
  - `layouts/page.tsx:505` — archive layout
  - `scenarios/page.tsx:336` — apply scenario (đã reword ở P0, giữ copy)
- Accessibility: `role="dialog"`, `aria-modal="true"`, focus restore on close.
- Styling: overlay + panel, dùng `--panel`, `--line`, `--red` cho danger variant.

**Không làm:**
- Nested dialogs
- Form trong dialog
- Animation phức tạp

**Verification:**
- Unit test: `confirm-dialog.test.tsx` — open/close, focus trap, escape, confirm/cancel callbacks, variants
- Manual: archive layout + apply scenario dùng dialog mới
- E2E: check `hosted-rbac.spec.ts` không assert `window.confirm` (nếu có, update)
- `npm run lint && npm run typecheck && npm test -- --run && npm run build`

**Effort estimate:** 3-4h

---

### CP7 — KPI Contextual Tooltips [Priority: MEDIUM]

**Vấn đề:** KPI cards dùng jargon ("Starvation", "Congestion") không giải thích. Non-domain user không interpret được.

**Scope:**
- Tạo `components/ui/tooltip.tsx`: hover/focus tooltip, CSS-only positioning (không floating-ui).
- Add tooltips vào `kpi-grid.tsx` cho mỗi card:
  - Throughput: "Số task hoàn thành/giờ. Cao hơn = tốt hơn."
  - Fleet online: "Số AMR đang hoạt động / tổng fleet."
  - Avg cycle: "Thời gian trung bình từ nhận task đến hoàn thành. Thấp hơn = tốt hơn."
  - Starvation: "Số lần station yêu cầu battery nhưng không có AMR khả dụng. 0 = lý tưởng; >5 = cần thêm fleet."
  - Congestion: "% thời gian zones vượt ngưỡng occupancy. Thấp hơn = tốt hơn."
- Tooltip trigger: hover trên desktop, tap trên mobile. Icon ⓘ nhỏ bên cạnh label.
- Accessibility: `aria-describedby` linking card to tooltip content.

**Không làm:**
- Chart trong tooltip
- Historical trend trong tooltip
- Configurable tooltip content

**Verification:**
- Unit test: `tooltip.test.tsx` — show/hide, aria, keyboard focus
- Manual: hover mỗi KPI card → tooltip hiện đúng nội dung
- `npm run lint && npm run typecheck && npm test -- --run && npm run build`

**Effort estimate:** 2-3h

---

### CP8 — Alert Management Controls [Priority: MEDIUM]

**Vấn đề:** Alert list read-only. Không filter severity, không acknowledge/dismiss. Gây alert fatigue.

**Scope:**
- Filter chips trong `alert-list.tsx`: All | Critical | Warning | Info. Default: All.
- Acknowledge button trên mỗi alert: gọi API `POST /api/v1/alerts/{id}/acknowledge` (nếu endpoint tồn tại; nếu không, local-only dismiss với toast "Acknowledged locally").
- Dismissed alerts ẩn khỏi list mặc định. Toggle "Show dismissed" để xem lại.
- Search input: filter by robot ID, task ID, hoặc message substring. Client-side filter.
- Sort: newest first (đã có), severity priority option.

**Backend dependency:** Check `apps/backend/src/ev_twin_api/api/` xem alert acknowledge endpoint tồn tại chưa. Nếu chưa, implement local-only trước, backend checkpoint riêng.

**Không làm:**
- Bulk acknowledge
- Alert rules/configuration UI
- Alert export

**Verification:**
- Unit test: `alert-list.test.tsx` — filter, search, acknowledge, sort
- Manual: tạo nhiều alerts → filter → acknowledge → verify ẩn/hiện
- `npm run lint && npm run typecheck && npm test -- --run && npm run build`

**Effort estimate:** 4-5h

---

### CP9 — Breadcrumb Navigation [Priority: LOW]

**Vấn đề:** Topbar luôn hiện "EV Factory Digital Twin". User sâu trong flow không biết mình ở đâu.

**Scope:**
- Tạo `components/layout/breadcrumbs.tsx`: simple breadcrumb trail.
- Define route hierarchy trong `lib/navigation.ts`:
  ```
  / → Overview
  /scenarios → Scenarios
  /scenarios?candidate=X → Scenarios > candidate-X
  /layouts → Layouts
  /layouts?id=X → Layouts > layout-X
  /commands → Commands
  /fleet → Fleet
  ```
- Parse pathname + searchParams để derive breadcrumbs.
- Position: trong topbar, thay thế hoặc bổ sung static title.
- Last item = current page (non-link). Others = links.
- Mobile: truncate middle items nếu > 3 levels.

**Không làm:**
- Editable breadcrumbs
- Dropdown menu cho siblings
- History-based breadcrumbs (chỉ route-based)

**Verification:**
- Unit test: `breadcrumbs.test.tsx` — parse routes, render levels, mobile truncation
- Manual: navigate deep → breadcrumbs đúng → click back → correct
- `npm run lint && npm run typecheck && npm test -- --run && npm run build`

**Effort estimate:** 2-3h

---

### CP10 — Data Freshness Indicator [Priority: LOW]

**Vấn đề:** Connection status badge nói LIVE/OFFLINE nhưng không nói dữ liệu cập nhật lần cuối khi nào.

**Scope:**
- Thêm `lastUpdateAt: number | null` vào `factory-store.ts`. Update mỗi khi nhận WS event hoặc REST snapshot.
- Trong topbar/cockpit: hiển thị "Updated 3s ago" / "Updated 2m ago" bên cạnh connection badge.
- Staleness threshold: nếu `lastUpdateAt` > 30s ago và status === "LIVE", hiện amber warning "Data may be stale".
- Format: relative time (< 60s → "Xs ago", < 60m → "Xm ago", else → timestamp).

**Không làm:**
- Per-entity freshness (chỉ global)
- Configurable thresholds
- Historical freshness chart

**Verification:**
- Unit test: freshness formatting, staleness detection
- Manual: mock telemetry → verify timestamp updates → stop → verify staleness warning
- `npm run lint && npm run typecheck && npm test -- --run && npm run build`

**Effort estimate:** 1-2h

---

## Priority Matrix

| CP | Priority | Effort | Impact | Dependencies | Should Do First? |
|----|----------|--------|--------|--------------|-----------------|
| CP1 Toast | CRITICAL | 4-6h | Rất cao — fix feedback gap lớn nhất | None | Yes |
| CP2 Offline Banner | CRITICAL | 2-3h | Rất cao — operational safety | None | Yes (song song CP1) |
| CP3 Onboarding | HIGH | 4-5h | Cao — reduce time-to-productivity | None | After CP1+CP2 |
| CP4 Pause/Resume | HIGH | 3-4h | Cao — operational control | None | After CP1+CP2 |
| CP5 Sim Progress | MEDIUM-HIGH | 2-3h | Trung bình-cao — reduce anxiety | CP1 (toast timeout) | After CP1 |
| CP6 Confirm Dialog | MEDIUM | 3-4h | Trung bình — visual consistency | None | Anytime |
| CP7 KPI Tooltips | MEDIUM | 2-3h | Trung bình — domain accessibility | CP7 tooltip component | After CP6 (shared UI pattern) |
| CP8 Alert Mgmt | MEDIUM | 4-5h | Trung bình — reduce alert fatigue | Possibly backend | After CP1 |
| CP9 Breadcrumbs | LOW | 2-3h | Thấp-trung bình — orientation | None | Anytime |
| CP10 Freshness | LOW | 1-2h | Thấp — nice-to-have | CP2 (connection infra) | Last |

## Execution Order Đề Xuất

```text
Phase 1 — Feedback & Safety (tuần 1)
  CP1 Toast ──────────────────┐
  CP2 Offline Banner ─────────┤ (song song, independent)
                              ↓
Phase 2 — Operational Controls (tuần 2)
  CP3 Onboarding ─────────────┐
  CP4 Pause/Resume ───────────┤ (song song, independent)
  CP5 Sim Progress ───────────┘ (needs CP1)
                              ↓
Phase 3 — Polish (tuần 3)
  CP6 Confirm Dialog ─────────┐
  CP7 KPI Tooltips ───────────┤
  CP8 Alert Management ───────┘
                              ↓
Phase 4 — Nice-to-have (tuần 4 hoặc defer)
  CP9 Breadcrumbs
  CP10 Freshness
```

## Tổng Effort

- Phase 1: 6-9h
- Phase 2: 9-12h
- Phase 3: 9-12h
- Phase 4: 3-5h
- **Total: 27-38h** (~4-5 ngày làm việc full-time)

## Quality Gate Mỗi Checkpoint

Mỗi CP phải pass trước khi bắt đầu CP tiếp theo:

```bash
cd apps/frontend
npm run lint          # 0 errors
npm run typecheck     # 0 errors
npm test -- --run     # all pass (existing + new)
npm run build         # production build success
```

Integration test (nếu CP touch WebSocket/store):
```bash
cd tests/integration
# run relevant integration tests
```

## Documentation Policy

Mỗi CP hoàn thành → tạo `docs/changes/improve-ux-cp{N}-{slug}.md` theo template chuẩn:
- Summary, Motivation, Architecture/Contract Impact, Files Changed, Verification, CI/Build Impact, Follow-up.

Update `docs/changes/improveUX.md` (file này) với progress tracker sau mỗi CP.

## Out of Scope

Những vấn đề UX đã được fixUX.md cover (KHÔNG làm lại):
- Candidate view model, NextActionStrip, workflow timeline, queue filter, route stepper, apply confirmation copy, layout comparison, zone editor, scenario settings basic/advanced, command timeline, optimization panel position, request-revision workflow.

Những vấn đề cần backend change riêng (KHÔNG nằm trong checkpoints này):
- Server-side simulation progress reporting
- Alert acknowledge API endpoint (nếu chưa có)
- Reject reason structured storage (P2 fixUX.md đã cover)
- Pagination/filter cho GET /scenarios (C8)

Những vấn đề architectural (KHÔNG nằm trong scope):
- Decompose god components (scenarios/page.tsx, factory-plant-map-2d.tsx)
- Typed AppState thay app.state + cast()
- Deep-copy optimization
- Structured logging / request correlation

## Progress Tracker

| CP | Status | Started | Completed | Notes |
|----|--------|---------|-----------|-------|
| CP1 Toast | Completed | 2026-08-30 | 2026-08-30 | 38 files / 176 tests; lint, typecheck, build passed. |
| CP2 Offline Banner | Completed | 2026-08-30 | 2026-08-30 | 39 files / 182 tests; lint, typecheck, build and manual smoke passed. |
| CP3 Onboarding | Completed | 2026-08-30 | 2026-08-30 | 40 files / 186 tests; lint, typecheck, build and role-aware manual smoke passed. |
| CP4 Pause/Resume | Completed | 2026-08-30 | 2026-08-30 | 42 files / 193 tests; lint, typecheck, build and MOCK/API manual smoke passed. |
| CP5 Sim Progress | Completed | 2026-08-30 | 2026-08-30 | 42 files / 196 tests; lint, typecheck, build and manual smoke passed. |
| CP6 Confirm Dialog | Pending | — | — | — |
| CP7 KPI Tooltips | Pending | — | — | — |
| CP8 Alert Mgmt | Pending | — | — | — |
| CP9 Breadcrumbs | Pending | — | — | — |
| CP10 Freshness | Pending | — | — | — |
