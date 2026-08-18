# Weekly Journal — Team [Tên Team]

> Ghi lại mỗi tuần: học được gì, khó khăn gì, quyết định gì, kế hoạch tiếp.

---

## Week 1: 13/08/2026 - 16/08/2026

### Mục tiêu tuần này
- [x] Hoàn thành monitoring realtime 2D từ FastAPI/WebSocket.
- [x] Nối SimPy benchmark vào backend và frontend.
- [x] Hoàn thành workflow human-in-the-loop tối thiểu trước khi apply.
- [ ] Rehearsal và deploy bản MVP.

### Đã hoàn thành
- Scenario API/UI: run, baseline comparison, approve, reject và apply.
- Apply trước approve trả HTTP 409; apply hợp lệ reset MockFactory.
- Simulation input được validate và cùng input cho kết quả deterministic.
- Dashboard API mode không trình bày fixture như dữ liệu backend.
- Operations Trend lấy mẫu 5 giây trong cửa sổ 5 phút; KPI vẫn cập nhật realtime.
- Quality gate: 185 Python tests và 21 frontend tests pass.

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Test async dùng default executor có thể treo khi chạy tuần tự | Giới hạn workload MVP và chạy benchmark deterministic trực tiếp; giữ test route/service không phụ thuộc transport lỗi | Toàn bộ 185 test chạy xong ổn định |
| SimPy và realtime mock có tham số khác nhau | Chỉ map `num_robots` và task interval; ghi rõ travel/loading là benchmark-only | Không tuyên bố sai khả năng apply |
| Phạm vi 3 ngày quá rộng | Khóa P0 theo vertical slice và hoãn 3D/ROS2/auth/database | Có luồng demo khép kín để rehearsal |

### Bài học
- Contract FE–BE phải được khóa trước khi hai phía triển khai song song.
- Human-in-the-loop cần được chứng minh bằng state transition và server-side guard,
  không chỉ bằng một nút trên giao diện.
- SimPy benchmark và MockFactory realtime có vai trò khác nhau; cần mô tả ranh giới
  trung thực trong demo.

### Kế hoạch tiếp theo trước hạn MVP
- [ ] Chạy smoke script và demo thủ công trên Chrome.
- [ ] Rehearsal luồng demo ít nhất hai lần.
- [ ] Deploy Render/Vercel hoặc xác nhận phương án demo local.
- [ ] Quay video dự phòng 3–5 phút.

---

## Week 2: [Ngày bắt đầu] - [Ngày kết thúc]

### Mục tiêu tuần này
- [ ] [Mục tiêu 1]

### Đã hoàn thành
-

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| | | |

### Bài học
-

### Kế hoạch tuần sau
-

---

<!-- Tiếp tục copy block trên cho Week 3, 4, 5, 6 -->
