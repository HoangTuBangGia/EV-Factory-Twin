import logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# INFO chỉ dành cho sự kiện vòng đời (startup/shutdown) và thay đổi trạng thái quan
# trọng. Dữ liệu tần suất cao (telemetry mỗi tick, mỗi frame WebSocket, ...) phải log
# ở DEBUG trở xuống — không đẩy lên INFO.


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT)
