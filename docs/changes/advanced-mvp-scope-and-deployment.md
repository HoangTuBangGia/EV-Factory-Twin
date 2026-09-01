# Advanced MVP Scope and Deployment

## Summary

Chốt MVP theo `TOPIC.md` với ROS2/Gazebo là runtime chính, SimPy là what-if
benchmark, và deployment tách thành Vercel, Render, Supabase và factory edge.

## Motivation

MVP trước đây mô tả mock factory và nhiều capability ngoài đề bài. Phạm vi mới
ưu tiên ROS2/Gazebo, đồng bộ hai chiều, 3D realtime, layout comparison, alert và
benchmark latency/FPS.

## Architecture / Contract Impact

- Mock factory chỉ còn là local/test fallback.
- Browser không giao tiếp trực tiếp với ROS DDS.
- Edge chạy Ubuntu 24.04 với ROS 2 Jazzy/Gazebo Harmonic/Nav2.
- Supabase PostgreSQL lưu scenario, layout, KPI và approval cần thiết.
- `pg_partman` không thuộc MVP.

## Files Changed

- `README.md`
- `docs/api.md`
- `docs/architecture.md`
- `docs/deployment.md`
- `docs/development.md`
- `evaluation/README.md`
- `docs/presentation/README.md`
- `docs/requirements.md`
- `docs/team-plan.md`

## Verification

Đã rà soát nội dung và tính nhất quán giữa TOPIC, requirements, architecture, API,
development, evaluation, presentation và deployment docs. Chưa chạy build vì
checkpoint này chỉ cập nhật tài liệu.

## CI / Build Impact

Không thay đổi CI hoặc runtime code. Các checkpoint implementation tiếp theo phải
thêm ROS build/test, backend integration test, frontend E2E và deployment smoke test.

## Follow-up

Implement ROS2 multi-AMR command path, layout API/SimPy integration, factory 3D main
page, latency/FPS measurement và Vercel/Render deployment manifests.
