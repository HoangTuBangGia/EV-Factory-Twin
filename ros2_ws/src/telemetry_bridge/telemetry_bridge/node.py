import http.client
import ipaddress
import json
import math
import os
import threading
import urllib.error
import urllib.request
from datetime import UTC, datetime
from urllib.parse import urlsplit

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.utilities import get_default_context
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String

STATUSES = {
    "IDLE",
    "MOVING",
    "MOVING_TO_PICKUP",
    "PICKING",
    "DELIVERING",
    "DROPPING",
    "MOVING_TO_CHARGER",
    "WAITING",
    "CHARGING",
    "ERROR",
    "OFFLINE",
}
RETRYABLE_STATUSES = {429}
MAX_ATTEMPTS = 4
MAX_BACKOFF_SECONDS = 1.0


class RejectRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def yaw_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    values = (x, y, z, w)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("quaternion components must be finite")
    norm = math.sqrt(sum(value * value for value in values))
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-3):
        raise ValueError("quaternion must have unit length")
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def iso_timestamp(now: datetime) -> str:
    return now.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def telemetry_endpoint(backend_url: str) -> str:
    parsed = urlsplit(backend_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("backend_url must be an HTTP(S) URL")
    try:
        loopback = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        loopback = parsed.hostname.lower() == "localhost"
    if parsed.scheme == "http" and not loopback:
        raise ValueError("remote backend_url must use HTTPS")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("backend_url must not contain credentials, query, or fragment")
    return backend_url.rstrip("/") + "/internal/v1/telemetry"


def is_retryable_status(status: int) -> bool:
    return status in RETRYABLE_STATUSES or 500 <= status <= 599


def encode_payload(
    robot_id: str, odom: Odometry, battery: float, status: str, now: datetime
) -> bytes:
    p, q, twist = odom.pose.pose.position, odom.pose.pose.orientation, odom.twist.twist
    scalars = (p.x, p.y, twist.linear.x, twist.angular.z, battery)
    if not all(math.isfinite(value) for value in scalars):
        raise ValueError("telemetry values must be finite")
    if not 0.0 <= battery <= 1.0:
        raise ValueError("battery percentage must be in [0, 1]")
    payload = {
        "timestamp": iso_timestamp(now),
        "robot_id": robot_id,
        "pose": {"x": p.x, "y": p.y, "yaw": yaw_from_quaternion(q.x, q.y, q.z, q.w)},
        "velocity": {"linear": twist.linear.x, "angular": twist.angular.z},
        "battery": battery * 100.0,
        "status": status,
        "task_id": None,
        "payload_id": None,
    }
    return json.dumps(payload, allow_nan=False, separators=(",", ":")).encode("utf-8")


class LatestWorker:
    def __init__(self, send, warning) -> None:
        self._send = send
        self._warning = warning
        self._condition = threading.Condition()
        self._pending: bytes | None = None
        self._stopping = False
        self._thread = threading.Thread(target=self._run, name="telemetry-http", daemon=True)
        self._thread.start()

    def submit(self, body: bytes) -> None:
        with self._condition:
            if not self._stopping:
                self._pending = body
                self._condition.notify()

    def close(self) -> None:
        with self._condition:
            self._stopping = True
            self._condition.notify_all()
        self._thread.join()

    def _wait_for_stop(self, seconds: float) -> bool:
        with self._condition:
            self._condition.wait_for(
                lambda: self._stopping,
                timeout=seconds,
            )
            return self._stopping

    def _deliver(self, body: bytes) -> None:
        for attempt in range(MAX_ATTEMPTS):
            try:
                status = self._send(body)
                retry = is_retryable_status(status)
                if not retry:
                    if status >= 300:
                        self._warning(f"telemetry rejected with HTTP {status}")
                    return
                detail = f"HTTP {status}"
            except (
                urllib.error.URLError,
                http.client.HTTPException,
                TimeoutError,
                OSError,
            ) as error:
                retry = True
                detail = str(error)
            if attempt == MAX_ATTEMPTS - 1:
                self._warning(f"telemetry delivery failed after {MAX_ATTEMPTS} attempts: {detail}")
                return
            backoff = min(0.1 * (2**attempt), MAX_BACKOFF_SECONDS)
            if self._wait_for_stop(backoff):
                return

    def _run(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._stopping or self._pending is not None)
                if self._stopping:
                    return
                body, self._pending = self._pending, None
            assert body is not None
            self._deliver(body)


class TelemetryBridge(Node):
    def __init__(self) -> None:
        super().__init__("telemetry_bridge")
        self._worker: LatestWorker | None = None
        self.declare_parameter("robot_id", os.getenv("AMR_ROBOT_ID", "AMR-01"))
        self.declare_parameter(
            "backend_url", os.getenv("TELEMETRY_BACKEND_URL", "http://localhost:8000")
        )
        self.declare_parameter("odom_topic", "odom")
        self.declare_parameter("battery_topic", "battery_state")
        self.declare_parameter("status_topic", "status")
        secret = os.getenv("EDGE_TELEMETRY_SHARED_SECRET")
        if not secret:
            raise RuntimeError("EDGE_TELEMETRY_SHARED_SECRET environment variable is required")
        endpoint = telemetry_endpoint(str(self.get_parameter("backend_url").value))
        opener = urllib.request.build_opener(RejectRedirectHandler())
        self._odom: Odometry | None = None
        self._battery = 1.0
        self._status = "IDLE"
        self._lock = threading.Lock()
        odom_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        state_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(
            Odometry, str(self.get_parameter("odom_topic").value), self._on_odom, odom_qos
        )
        self.create_subscription(
            BatteryState,
            str(self.get_parameter("battery_topic").value),
            self._on_battery,
            state_qos,
        )
        self.create_subscription(
            String, str(self.get_parameter("status_topic").value), self._on_status, state_qos
        )
        self.create_timer(0.1, self._queue_latest)

        def send(body: bytes) -> int:
            request = urllib.request.Request(
                endpoint,
                body,
                {"Content-Type": "application/json", "Authorization": "Bearer " + secret},
            )
            try:
                with opener.open(request, timeout=2) as response:
                    return response.status
            except urllib.error.HTTPError as error:
                return error.code

        self._worker = LatestWorker(send, self.get_logger().warning)

    def _on_odom(self, message: Odometry) -> None:
        with self._lock:
            self._odom = message

    def _on_battery(self, message: BatteryState) -> None:
        if math.isfinite(message.percentage) and 0.0 <= message.percentage <= 1.0:
            with self._lock:
                self._battery = message.percentage
        else:
            self.get_logger().warning("ignoring BatteryState percentage outside [0, 1]")

    def _on_status(self, message: String) -> None:
        if message.data in STATUSES:
            with self._lock:
                self._status = message.data

    def _queue_latest(self) -> None:
        with self._lock:
            odom, battery, status = self._odom, self._battery, self._status
            self._odom = None
        if odom is None or self._worker is None:
            return
        try:
            body = encode_payload(
                str(self.get_parameter("robot_id").value),
                odom,
                battery,
                status,
                datetime.now(UTC),
            )
        except ValueError as error:
            self.get_logger().warning(f"dropping invalid telemetry: {error}")
            return
        self._worker.submit(body)

    def destroy_node(self):
        if self._worker is not None:
            self._worker.close()
            self._worker = None
        return super().destroy_node()


def main(args=None) -> None:
    node = None
    rclpy.init(args=args)
    try:
        node = TelemetryBridge()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        get_default_context().try_shutdown()
