# Structured Scenario Revision Workflow

## Summary

P2.1 bổ sung contract backend cho Monitor yêu cầu sửa một scenario đã submit. Scenario gốc chuyển
sang `REVISION_REQUESTED` với ghi chú bắt buộc; Designer chạy một benchmark mới, bất biến, liên kết
về bản gốc qua `revision_of`.

## Motivation

Workflow cũ kết thúc ở `REJECTED`, không lưu lý do và không cho biết scenario chạy lại kế thừa từ
candidate nào. Việc sửa trực tiếp benchmark cũ cũng sẽ làm sai lịch sử KPI và audit.

## Architecture / Contract Impact

- Thêm status `REVISION_REQUESTED` bằng migration riêng trước khi constraint sử dụng giá trị mới.
- `public.scenarios` có `review_note` và self-reference `revision_of`.
- `public.scenario_reviews` lưu quyết định và note bất biến qua trigger hiện có.
- `POST /api/v1/scenarios/{id}/request-revision` dành cho Monitor, body `{ "note": "..." }`.
- `POST /api/v1/scenarios/run` nhận `revision_of`; chỉ creator của scenario đang
  `REVISION_REQUESTED` được tạo revision liên kết.
- Endpoint `/reject` và status `REJECTED` được giữ để tương thích.
- SimPy, KPI authoritative, runtime apply và ROS contract không đổi.

## Files Changed

- `supabase/migrations/20260828000100_add_revision_requested_status.sql`
- `supabase/migrations/20260828000200_add_scenario_revision_workflow.sql`
- Backend scenario schema, repository, service, API và audit action.
- Frontend Zod/workflow compatibility cho status và field mới.
- Backend, migration và frontend workflow regression tests.

## Verification

- Backend/migration targeted tests: 64 pass.
- Full Pytest với repository in-memory: 424 pass, 2 PostgreSQL integration tests skip do không có
  `TEST_DATABASE_URL`.
- Ruff: pass.
- Mypy workspace: pass, 89 source files.
- Frontend ESLint và TypeScript: pass.
- Frontend targeted tests: 25 pass; full Vitest: 37 files, 166 tests pass.
- Next.js production build: pass, 14/14 pages.

Full Pytest với `DATABASE_URL` hiện tại không phải gate hợp lệ trước migration: database đó chưa có
`review_note`/`revision_of`, nên startup thất bại đúng như contract mới dự kiến. Hai migration P2.1
phải được apply trước khi deploy backend mới.

## CI / Build Impact

Database CI phải apply hai migration mới theo thứ tự. Backend API và frontend parser nhận thêm status
nhưng không đổi contract telemetry, layout hoặc command.

## Follow-up

P2.2 sẽ thêm form note cho Monitor, hiển thị feedback cho Designer và nút tạo revision đã điền sẵn
dữ liệu candidate gốc.
