# Tên Đề Tài
Factory Twin - Digital twin nhà máy/robot để mô phỏng & giám sát vận hành
# Mô Tả Bài Toán
"📍 Thực trạng: Vận hành đội robot trong nhà máy cần thử nghiệm bố trí, luồng di chuyển và kịch bản trước khi triển khai thật, đồng thời giám sát trạng thái theo thời gian thực, nhưng thiếu một bản sao số thống nhất để làm cả hai.

🎯 Vấn đề: Xây dựng digital twin của một khu vực nhà máy/kho với robot di động, cho phép mô phỏng bố trí và luồng công việc, đồng thời phản chiếu trạng thái robot (vị trí, trạng thái, cảnh báo) từ dữ liệu/telemetry mô phỏng lên giao diện giám sát 3D.

🔒 Ràng buộc: kỹ sư duyệt các thay đổi bố trí/kịch bản trước khi áp dụng (human-in-the-loop); mọi thử nghiệm điều khiển chỉ trên digital twin/mô phỏng, không tác động robot thật khi chưa validate; chỉ số đo được (throughput luồng công việc, thời gian chu trình, tỷ lệ tắc nghẽn/va chạm mô phỏng, độ trễ cập nhật trạng thái); tối ưu hiệu năng render và tần suất cập nhật realtime; bảo mật dữ liệu telemetry và cấu hình nhà máy."

# Tech stack gợi ý

• Python
• Gazebo hoặc Isaac Sim
• ROS2 cho telemetry và điều phối robot
• FastAPI backend + WebSocket
• React/Next.js + three.js/WebGL cho giám sát 3D
• time-series DB (hoặc lưu log) cho telemetry
• Docker + GPU."

# Yêu cầu đầu ra (Cơ bản + Nâng cao) - gợi ý
"Cơ bản:
• digital twin một khu vực với vài robot mô phỏng, giao diện 3D hiển thị vị trí/trạng thái realtime, cho phép đổi bố trí và chạy lại, ≥2 vai trò (người thiết kế và người giám sát), báo cáo throughput/thời gian chu trình.

Nâng cao:
• đồng bộ hai chiều với mô phỏng ROS2 nhiều robot, phát cảnh báo khi bất thường, chạy so sánh các phương án bố trí và tối ưu luồng, benchmark hiệu năng và độ trễ cập nhật."

