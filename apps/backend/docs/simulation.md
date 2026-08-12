# Xưởng mô phỏng hoạt động theo quy tắc gì

File này mô tả **hành vi** của xưởng: robot đi đâu, đơn hàng chạy qua những
bước nào, pin hao ra sao, khi nào có cảnh báo. Kèm đầy đủ con số cụ thể.

## Mặt bằng xưởng

Xưởng rộng **20 m × 15 m**. Có đúng 6 vị trí, toạ độ **cố định tuyệt đối** —
khởi động lại backend bao nhiêu lần cũng ra y hệt, không có yếu tố ngẫu nhiên
nào trong toàn bộ hệ thống.

```
  y
 15 ┼──────────────────────────────────────────────┐
    │                                              │
 12 │  ⚡CHARGING      🅿IDLE_ZONE                   │
    │   (2,12)         (5,12)                      │
    │                                              │
  8 │              ·INTERSECTION_B    🔧MARRIAGE    │
    │                  (12,8)          (16,8)      │
    │                                              │
  4 │  📦BATTERY_BUFFER  ·INTERSECTION_A            │
    │      (2,4)            (8,4)                  │
  0 └──────────────────────────────────────────────┘
    0        5        10       15       20  x
```

| ID | Tên | `type` | Toạ độ | Để làm gì |
|---|---|---|---|---|
| `BATTERY_BUFFER` | Battery Buffer | `BUFFER` | (2, 4) | Kho pin — nơi robot **lấy** pin |
| `INTERSECTION_A` | Intersection A | `WAYPOINT` | (8, 4) | Điểm rẽ trên đường, robot chỉ đi qua |
| `INTERSECTION_B` | Intersection B | `WAYPOINT` | (12, 8) | Điểm rẽ trên đường, robot chỉ đi qua |
| `MARRIAGE_STATION` | Marriage Station | `MARRIAGE` | (16, 8) | Trạm lắp pin vào xe — nơi robot **trả** pin |
| `CHARGING_STATION` | Charging Station | `CHARGER` | (2, 12) | Trạm sạc cho chính robot |
| `IDLE_ZONE` | Idle Zone | `IDLE` | (5, 12) | Khu chờ — nơi robot xuất hiện lúc khởi tạo |

> "Marriage station" là thuật ngữ trong ngành ô tô: chỉ công đoạn ghép khối pin
> vào khung xe.

**Vị trí robot lúc khởi tạo:** 5 robot đứng thành hàng ngang tại khu chờ, cách
nhau đúng 1 m — AMR-01 ở (5, 12), AMR-02 ở (6, 12), ... AMR-05 ở (9, 12). Giãn
ra như vậy để chúng không chồng lên nhau một điểm khi frontend vẽ.

## Robot có 10 trạng thái

| Trạng thái | Nghĩa là gì | Có xảy ra trong bản mock không? |
|---|---|---|
| `IDLE` | Rảnh, chờ việc | ✅ |
| `MOVING_TO_PICKUP` | Đang đi tới kho pin để lấy hàng | ✅ |
| `PICKING` | Đang lấy pin lên | ✅ |
| `DELIVERING` | Đang chở pin tới trạm lắp | ✅ |
| `DROPPING` | Đang hạ pin xuống | ✅ |
| `MOVING_TO_CHARGER` | Pin yếu, đang đi tới trạm sạc | ✅ |
| `CHARGING` | Đang sạc | ✅ |
| `WAITING` | (dành cho tương lai) | ❌ không bao giờ |
| `ERROR` | (dành cho tương lai) | ❌ không bao giờ |
| `OFFLINE` | (dành cho tương lai) | ❌ không bao giờ |

> **Frontend chú ý:** 3 trạng thái cuối có trong hợp đồng dữ liệu vì hệ thống
> thật sau này sẽ cần, nhưng bản mock hiện tại **không có đường nào dẫn tới
> chúng**. Đừng mất công làm giao diện cho 3 trạng thái đó ở giai đoạn này.

## Vòng đời một đơn chở pin

Đơn hàng và robot đổi trạng thái **song song, khớp từng bước với nhau**:

```
ĐƠN HÀNG                         ROBOT
─────────                        ─────
QUEUED       (vừa sinh ra)       IDLE
   │ hệ thống chọn được robot
   ▼
ASSIGNED                         MOVING_TO_PICKUP
   │ robot tới kho pin
   ▼
PICKUP                           PICKING
   │ lấy pin xong  → robot được gắn payload_id
   ▼
IN_PROGRESS                      DELIVERING
   │ robot tới trạm lắp
   ▼
DELIVERED                        DROPPING
   │ hạ pin xong  → robot nhả payload_id
   ▼
COMPLETED                        IDLE   (rảnh, nhận đơn tiếp)
```

Ngoài ra `TaskStatus` còn giá trị `FAILED`, nhưng bản mock hiện chưa có tình
huống nào làm đơn thất bại.

**Mốc thời gian được ghi lại:**

- `created_at` — lúc đơn được sinh ra
- `started_at` — lúc đơn được gán cho robot
- `completed_at` — lúc hạ pin xong

**`PICKING` và `DROPPING` kéo dài đúng 1 tick** (1/10 giây thật). Ngắn, nhưng
đủ để frontend nhìn thấy trạng thái đó ít nhất một lần.

## Robot di chuyển thế nào

Không có thuật toán tìm đường, không mô phỏng va chạm. Robot chỉ **bám theo
một chuỗi điểm mốc (waypoint) cố định**.

**Tuyến chở pin** `BATTERY_BUFFER → MARRIAGE_STATION`:

```
(2,4) ──→ (8,4) ──→ (12,8) ──→ (16,8)
kho pin   ngã A     ngã B     trạm lắp
```

**Tuyến đi sạc** chỉ có 1 điểm: đi thẳng từ chỗ đang đứng tới (2, 12).

Mỗi tick, robot đi được `robot_speed_mps × dt` mét về phía điểm mốc kế tiếp.
Hướng quay đầu (`yaw`) tính bằng `atan2(Δy, Δx)` — luôn hướng về điểm đang nhắm
tới.

**Khi nào coi là "đã tới nơi"?** Nếu quãng đường đi được trong tick này ≥ khoảng
cách còn lại, robot được đặt **chính xác** vào toạ độ điểm mốc (không xê dịch lẻ
tẻ), phần dư bị bỏ, và tick sau mới nhắm điểm tiếp theo. Nhờ vậy dù chạy nhanh
tới đâu, robot cũng **không bao giờ nhảy cóc bỏ qua một điểm mốc nào**.

**Một điều dễ thắc mắc:** làm sao robot từ khu chờ (5, 12) tới được kho pin
(2, 4)? Nó đi thẳng — chặng "từ vị trí hiện tại tới waypoint đầu tiên" chính là
đoạn `MOVING_TO_PICKUP`, không cần cơ chế riêng nào.

**Và sau khi giao xong thì sao?** Robot **ở lại luôn tại trạm lắp (16, 8)**,
không tự quay về khu chờ — vì hiện chưa có tuyến đường ngược. Nó vẫn hoàn toàn
sẵn sàng nhận đơn mới ngay từ chỗ đang đứng.

## Đơn hàng được sinh và giao cho ai

**Sinh đơn:** cứ mỗi `task_interval_seconds` giây mô phỏng (mặc định 8), một
đơn mới ra đời ở trạng thái `QUEUED`.

ID đánh số tuần tự, không nhảy số: `TASK-0001`, `TASK-0002`, ... Mỗi đơn kèm
một mã kiện pin tương ứng: `BP-0001`, `BP-0002`, ...

**Chọn robot** (chạy mỗi tick, lặp tới khi không còn ghép được cặp nào):

1. Lọc ra các robot đang `IDLE`
2. **Loại bỏ robot có pin ≤ ngưỡng pin yếu** (mặc định 20%)
3. Trong số còn lại, chọn con **gần kho pin nhất** (khoảng cách đường chim bay)
4. Giao cho nó **đơn cũ nhất** đang chờ

Nếu không có robot nào đủ điều kiện, **đơn vẫn nằm im ở `QUEUED`** — không bị
huỷ, không báo lỗi. Tick sau hệ thống thử lại.

> Đây là thuật toán đơn giản có chủ ý. Không tối ưu hoá đội xe nâng cao ở giai
> đoạn này.

## Pin và sạc

> ⚠️ **Các con số dưới đây là tham số minh hoạ cho demo, không phải mô hình pin
> thật.** Chúng được cố ý làm nhanh để xem được cả chu kỳ sạc trong vài chục
> giây, thay vì vài tiếng.

**Tốc độ thay đổi pin, tính theo mỗi giây mô phỏng:**

| Robot đang | Pin thay đổi |
|---|---|
| Di chuyển (kể cả đi sạc) | **−0.5 %/giây** |
| `PICKING` hoặc `DROPPING` | **−0.2 %/giây** |
| `IDLE` | **0** (coi như không đáng kể) |
| `CHARGING` | **+5 %/giây** |

Pin **luôn bị kẹp trong khoảng 0–100** — không bao giờ âm, không bao giờ vượt
100, kể cả khi `dt` rất lớn.

**Chu trình đi sạc:**

```
IDLE + pin ≤ 20%
   ↓
MOVING_TO_CHARGER   (đi thẳng tới (2,12), vẫn hao 0.5%/giây trên đường)
   ↓ tới nơi
CHARGING            (+5%/giây)
   ↓ đạt 80%
IDLE                (sẵn sàng nhận đơn, vẫn đứng tại trạm sạc)
```

Ngưỡng pin yếu **20%** đọc từ config nên đổi được; mức sạc đầy **80%** là hằng
số trong code.

Lưu ý: robot pin yếu **không bị cấm hoạt động** — nó chỉ **không được giao đơn
mới**. Đơn đang chở dở vẫn chạy tiếp tới khi xong.

## Số liệu (metrics)

Tính lại **mỗi tick**, nên `GET /api/v1/metrics` luôn mới. Riêng bản đẩy qua
WebSocket thì ~1 lần/giây cho đỡ ngập.

| Chỉ số | Cách tính |
|---|---|
| `completed_tasks` | Đếm đơn ở trạng thái `COMPLETED` |
| `throughput_per_hour` | `số đơn xong ÷ số giờ MÔ PHỎNG đã trôi` |
| `average_cycle_time_seconds` | Trung bình của `completed_at − created_at` |
| `active_tasks` | Đơn đang chạy (không tính `QUEUED`/`COMPLETED`/`FAILED`) |
| `queued_tasks` | Đơn đang chờ |
| `starvation_events` | Số đơn từng phải chờ quá lâu (xem bên dưới) |
| `fleet_utilization_percent` | `robot đang làm việc ÷ robot online × 100` |

"Robot đang làm việc" gồm đúng 4 trạng thái: `MOVING_TO_PICKUP`, `PICKING`,
`DELIVERING`, `DROPPING`. Robot đang đi sạc **không** được tính là đang làm việc.

Ví dụ kiểm chứng: 2 đơn hoàn thành trong 120 giây mô phỏng → throughput = 60
đơn/giờ. Hai đơn có thời gian chu kỳ 40 s và 60 s → trung bình 50 s.

Chia cho 0 đã được xử lý: khi chưa có giây nào trôi qua, throughput trả về 0.0
chứ không lỗi.

## Cảnh báo (alerts)

| Mã | Mức độ | Phát khi |
|---|---|---|
| `LOW_BATTERY` | WARNING | Pin một robot rơi xuống ≤ ngưỡng (mặc định 20%) |
| `TASK_BACKLOG` | WARNING | Số đơn đang chờ **nhiều hơn số robot** |
| `STARVATION` | WARNING | Một đơn nằm chờ quá **30 giây thật** |
| `ROBOT_WAITING` | INFO | Một robot rảnh liên tục quá **2× `task_interval_seconds`** |
| `ROBOT_ERROR` | CRITICAL | Robot vào trạng thái `ERROR` — **thực tế không bao giờ xảy ra** ở bản mock |

ID cảnh báo đánh số tuần tự: `ALERT-0001`, `ALERT-0002`, ...

### Chống spam — phần quan trọng nhất

Engine chạy 10 lần/giây. Nếu cứ thấy pin yếu là phát cảnh báo, bạn sẽ nhận 10
cảnh báo mỗi giây cho cùng một con robot. Nên hệ thống dùng quy tắc:

> **Cảnh báo chỉ phát đúng một lần, vào khoảnh khắc "bước vào" tình trạng đó.**

Cụ thể với `LOW_BATTERY:AMR-01`:

```
pin 25% → 19%   ✅ phát 1 cảnh báo
pin vẫn 15%     ❌ im lặng (đã báo rồi)
pin vẫn 12%     ❌ im lặng
sạc lên 80%     — hệ thống ghi nhận "đã thoát khỏi tình trạng"
pin lại tụt 18% ✅ phát cảnh báo MỚI
```

Các loại cảnh báo khác cũng theo đúng nguyên tắc này. Riêng `STARVATION` thì
không cần "thoát khỏi tình trạng", vì một đơn đã được giao thì không bao giờ
quay lại hàng chờ nữa.

## Bảng tham số điều chỉnh được

Đổi qua `POST /api/v1/mock/config` hoặc biến môi trường lúc khởi động:

| Tham số | Mặc định | Cho phép | Ý nghĩa |
|---|---|---|---|
| `robot_count` | 5 | 1–10 | Số AMR |
| `task_interval_seconds` | 8.0 | 1.0–60.0 | Bao lâu sinh 1 đơn |
| `robot_speed_mps` | 1.2 | 0.1–3.0 | Tốc độ robot (m/s) |
| `simulation_speed` | 1.0 | 0.25–10.0 | Hệ số tăng tốc thời gian |
| `low_battery_threshold` | 20.0 | 0–100 | Ngưỡng pin yếu (%) |

**Lưu ý:** `robot_count` chỉ có tác dụng lúc khởi tạo, nên đổi nó xong phải gọi
thêm `POST /api/v1/mock/reset` mới thấy số robot thay đổi. Bốn tham số còn lại
có hiệu lực ngay ở tick kế tiếp.

## Muốn xem nhanh toàn bộ vòng đời?

```bash
curl -X POST localhost:8000/api/v1/mock/config \
  -H 'Content-Type: application/json' \
  -d '{"simulation_speed": 10, "task_interval_seconds": 2, "robot_speed_mps": 3}'

# theo dõi 1 robot đổi trạng thái
watch -n 0.5 "curl -s localhost:8000/api/v1/robots/AMR-01 | python3 -m json.tool"
```
