# Factory Twin — UI/UX Design Pack

Thư mục này chứa bản thiết kế độc lập cho Factory Twin. Nội dung ở đây không phụ thuộc vào framework frontend, FastAPI, Three.js, Gazebo hay ROS2.

## Mục tiêu sản phẩm

Factory Twin là bản sao số cho khu vực nhà máy/kho sử dụng AGV. Kỹ sư có thể quan sát, tạo thay đổi, chạy mô phỏng và so sánh kết quả trước khi một người có thẩm quyền phê duyệt triển khai xuống hệ thống thật.

Nguyên tắc bất biến:

> Không có thay đổi nào được triển khai xuống robot thật nếu chưa có simulation run thành công, risk report và quyết định phê duyệt của con người.

## Nội dung

- `flows/ui-flow.md`: user journey, trạng thái và các nhánh thao tác.
- `wireframes/wireframes.md`: wireframe thô cho các màn hình chính.
- `prototype/`: prototype HTML tĩnh có thể bấm thử, không cần cài dependency.
- `contracts/integration-boundaries.md`: ranh giới giữa UI, backend mô phỏng và ROS2.

## Chạy prototype

Mở trực tiếp `prototype/index.html` trong trình duyệt. Prototype chỉ dùng HTML/CSS/JavaScript thuần và dữ liệu giả lập.

## Phạm vi phiên bản đầu

1. Đăng nhập giả lập và chọn site.
2. Giám sát Live 3D bằng placeholder canvas.
3. Tạo và chạy một kịch bản mô phỏng.
4. So sánh baseline với candidate.
5. Bật lớp hiển thị Bottleneck/Drift.
6. Gửi duyệt, phê duyệt hoặc từ chối.
7. Mô phỏng bước xếp hàng triển khai; không gửi lệnh thật.
8. Chọn AGV trên mặt bằng để xem telemetry, nhiệm vụ, đích đến và hướng di chuyển.

## Visual direction

Prototype sử dụng phong cách **Modern SaaS · Glassmorphism · Structured Grid · Data-Driven · Corporate Blue · Light**. Hệ thống design token tập trung ở `prototype/styles.css`; phần HTML và luồng nghiệp vụ không phụ thuộc vào theme này.

## Quy ước an toàn UX

- `SIMULATION` và `LIVE` luôn có nhãn rõ ràng.
- Nút triển khai không nằm trên màn hình giám sát thông thường.
- Người tạo kịch bản không mặc định là người phê duyệt.
- Mỗi quyết định cần người thực hiện, thời gian, ghi chú và mã simulation run.
- UI chỉ gửi ý định triển khai; ROS2 adapter chịu trách nhiệm kiểm tra và thực thi ở lớp tích hợp.
