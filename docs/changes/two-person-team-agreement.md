# Two-Person Team Agreement

## Summary

Thay kế hoạch bốn người bằng agreement cho team hai người: một người phụ trách
Backend/ROS2 và một người phụ trách Frontend/Three.js.

## Motivation

Team thực tế có hai thành viên và cần một source of truth chung cho ownership,
API contract, quy trình đổi schema, UI direction và Definition of Done.

## Architecture / Contract Impact

Không thay đổi runtime contract. Tài liệu phân biệt contract đang chạy trong
`docs/api.md` với target contract cho layout checkpoint. Video Commercial Digital
Twin được dùng làm visual reference, không phải yêu cầu CAD/BIM hoặc pixel-perfect.

## Files Changed

- `docs/team-plan.md`
- `docs/changes/two-person-team-agreement.md`

## Verification

- `git diff --check`

## CI / Build Impact

Không thay đổi code, dependency, CI hoặc deployment configuration.

## Follow-up

Hai thành viên review agreement, điền người phụ trách thực tế và khóa layout API
trong `docs/api.md` trước khi frontend triển khai editor.
