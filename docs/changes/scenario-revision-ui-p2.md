# Scenario Revision UI

## Summary

P2.2 nối workflow revision P2.1 vào trang Scenarios. Monitor yêu cầu thay đổi bằng feedback bắt
buộc; Designer thấy feedback, mở một form đã điền từ candidate gốc và chạy benchmark mới có
`revision_of`.

## Motivation

Contract P2.1 đã bỏ ngõ cụt backend nhưng chưa có happy path trong browser. Người dùng vẫn phải gọi
API thủ công và tự sao chép cấu hình, dễ mất liên kết audit hoặc chọn sai layout version.

## Architecture / Contract Impact

- API client gọi `POST /api/v1/scenarios/{id}/request-revision` với note đã trim và validate.
- Monitor thấy textarea và `Request changes` trên candidate `SUBMITTED`; legacy reject endpoint vẫn
  tồn tại nhưng không còn là action chính trong UI.
- Chỉ creator thấy `Create revised candidate` trên candidate `REVISION_REQUESTED`.
- Form tải đúng immutable `layout_id`/`layout_version`, điền lại assumptions và gửi hidden
  `revision_of`. Designer vẫn có thể chọn layout/version khác trước khi chạy.
- Backend, database, SimPy, KPI, command và telemetry contract không đổi trong checkpoint này.

## Files Changed

- Frontend scenario schema và API client.
- Scenario actions, run form, page state và styles.
- Component, page, schema và API-client regression tests.
- `docs/changes/fixUX.md` và tài liệu checkpoint này.

## Verification

- ESLint: pass.
- TypeScript: pass. Một lần chạy song song với `next build` gặp race do build tái tạo
  `.next/types`; chạy lại tuần tự sau build pass sạch.
- Targeted Vitest: 5 files, 32 tests pass.
- Full Vitest: 37 files, 171 tests pass.
- Next.js production build: pass, 14/14 pages.

## CI / Build Impact

Không thêm dependency hoặc route frontend. Frontend deployment yêu cầu backend và hai migration
P2.1 đã được deploy trước.

## Follow-up

P2 hoàn tất. Usability test nên xác nhận Monitor viết feedback đủ cụ thể và Designer nhận ra
candidate mới vẫn phải submit lại.
