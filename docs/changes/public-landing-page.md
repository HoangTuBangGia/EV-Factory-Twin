# Public Product Landing Page

## Summary

Thêm landing page công khai tại `/homepage` để giới thiệu RAV-11 Factory Twin trước khi người dùng đăng nhập. Cockpit 3D hiện tại tiếp tục sử dụng route `/`.

## Motivation

Route gốc trước đây chuyển thẳng người dùng chưa xác thực tới form đăng nhập, nên giám khảo và người dùng mới không có ngữ cảnh về mục tiêu, năng lực và workflow của sản phẩm.

## Architecture / Contract Impact

- `/homepage`, `/login` và `/scene-probe` không sử dụng protected application frame.
- Request chưa xác thực tới `/` được chuyển sang `/homepage`.
- Các route nghiệp vụ khác vẫn chuyển sang `/login` và giữ `returnTo`.
- Không thay đổi API, database hoặc domain contract.

## Files Changed

- `apps/frontend/src/app/homepage/page.tsx`
- `apps/frontend/src/app/homepage/page.test.tsx`
- `apps/frontend/src/app/globals.css`
- `apps/frontend/src/middleware.ts`
- `apps/frontend/src/middleware.test.ts`
- `apps/frontend/src/components/auth/auth-provider.tsx`
- `apps/frontend/src/components/layout/application-frame.tsx`

## Verification

- Targeted: 4 files / 11 tests passed.
- `npm --prefix apps/frontend run lint`: passed.
- `npm --prefix apps/frontend run typecheck`: passed.
- `npm --prefix apps/frontend test -- --run --reporter=dot`: 47 files / 220 tests passed.
- `npm --prefix apps/frontend run build`: passed; 15/15 pages generated, including static `/homepage`.
- Manual desktop/mobile smoke: pending human review.

## CI / Build Impact

Frontend CI sẽ kiểm tra route mới bằng Vitest và Next.js production build. Không có dependency mới.

## Follow-up

Manual smoke trên desktop/mobile: `/homepage` công khai, CTA tới `/login`, người chưa đăng nhập vào `/` quay về `/homepage`, và tài khoản hợp lệ vẫn mở được cockpit `/`.
