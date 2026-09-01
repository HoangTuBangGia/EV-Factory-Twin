# Hosted Revision Workflow Acceptance

## Summary

P3 chuẩn bị acceptance gate cho workflow P0–P2: hosted Playwright đi qua cả hai role và nhánh
revision; RBAC regression bao phủ endpoint mới; runbook định nghĩa sáu phiên usability bắt buộc.

## Motivation

Unit/component tests chứng minh logic riêng lẻ nhưng không chứng minh hai tài khoản thật, Supabase,
database migrations, FastAPI và browser hoạt động nhất quán. UX audit cũng yêu cầu quan sát người
dùng thật, không chỉ kiểm tra selector.

## Architecture / Contract Impact

- Không đổi runtime/API/database contract.
- Hosted E2E vẫn dùng local FastAPI/Next.js với Supabase staging và chạy serial để chia sẻ candidate.
- Suite không cleanup scenario tự động vì API không có delete; tên timestamped tránh collision và
  staging data được giữ làm audit evidence.
- Trace, screenshot và video tiếp tục bị tắt để không lưu credential/token.

## Files Changed

- `apps/frontend/e2e/hosted-rbac.spec.ts`
- `apps/frontend/playwright.config.ts`
- `apps/backend/tests/api/test_auth_rbac.py`
- `docs/runbooks/workflow-usability-acceptance.md`
- `docs/development.md`
- `docs/changes/fixUX.md`
- `docs/changes/hosted-revision-acceptance-p3.md`

## Verification

- Targeted backend RBAC: 67 tests pass với repository in-memory.
- Ruff: pass.
- Frontend ESLint và TypeScript: pass.
- `npm run test:e2e:list`: nhận 5 test trong 2 file, gồm scene smoke và 4 bước hosted revision.
- Scene smoke pass cả khi chạy riêng và trong full E2E sau khi suite mặc định dùng cùng SwiftShader
  flags với frontend smoke suite.
- Lần chạy hosted đầu tiên với đủ bốn biến credential đã đi vào flow nhưng dừng ở selector email:
  các nút copy credential cũng khớp `getByLabel("Email")`. Helper login nay định vị trực tiếp hai
  input ổn định `#login-email` và `#login-password`; cần chạy lại để xác nhận toàn bộ flow.
- Hosted E2E execution và sáu phiên human usability vẫn pending.

## CI / Build Impact

CI hosted job tự chạy flow mới khi đủ bảy staging secrets. Khi thiếu secrets, job giữ hành vi skip
có giải thích. Staging database phải được migrate trước khi job chạy.

## Follow-up

Apply migrations P2.1 to staging, run hosted E2E, conduct D1–D3/M1–M3 sessions, then record the
actual run link, observations and `PASS`/`FAIL` decision in the runbook.
