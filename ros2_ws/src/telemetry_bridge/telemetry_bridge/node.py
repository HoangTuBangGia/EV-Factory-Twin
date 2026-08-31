import http.client
import ipaddress
import json
import math
import os
import threading
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

import rclpy
from amr_interfaces.msg import TaskState
from amr_interfaces.srv import ApplyScenario, CreateTransportTask
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
HTTP_TIMEOUT_SECONDS = 5.0


@dataclass
class RobotSnapshot:
    robot_id: str
    namespace: str
    odom: Odometry | None = None
    battery: float = 1.0
    status: str = "IDLE"
    task_id: str = ""
    payload_id: str = ""


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


def edge_endpoint(backend_url: str, path: str) -> str:
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
    return backend_url.rstrip("/") + path


def telemetry_endpoint(backend_url: str) -> str:
    return edge_endpoint(backend_url, "/internal/v1/telemetry")


def is_retryable_status(status: int) -> bool:
    return status in RETRYABLE_STATUSES or 500 <= status <= 599


def load_robot_snapshots(path: str | Path) -> dict[str, RobotSnapshot]:
    with Path(path).open(encoding="utf-8") as config_file:
        document = json.load(config_file)
    robots = document.get("robots") if isinstance(document, dict) else None
    if not isinstance(robots, list) or not robots:
        raise ValueError("robots config must contain a non-empty robots array")
    snapshots: dict[str, RobotSnapshot] = {}
    namespaces: set[str] = set()
    for index, robot in enumerate(robots):
        if not isinstance(robot, dict):
            raise ValueError(f"robots[{index}] must be an object")
        robot_id, namespace = robot.get("robot_id"), robot.get("namespace")
        if not isinstance(robot_id, str) or not robot_id:
            raise ValueError(f"robots[{index}].robot_id must be a non-empty string")
        if not isinstance(namespace, str) or not namespace or "/" in namespace:
            raise ValueError(f"robots[{index}].namespace must be one ROS name segment")
        if robot_id in snapshots or namespace in namespaces:
            raise ValueError("robot IDs and namespaces must be unique")
        snapshots[robot_id] = RobotSnapshot(robot_id, namespace)
        namespaces.add(namespace)
    return snapshots


def encode_payload(
    robot_id: str,
    odom: Odometry,
    battery: float,
    status: str,
    now: datetime,
    task_id: str | None = None,
    payload_id: str | None = None,
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
        "task_id": task_id or None,
        "payload_id": payload_id or None,
    }
    return json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()


class DeliveryWorker:
    def __init__(self, send, warning, result=None) -> None:
        self._send = send
        self._warning = warning
        self._result = result or (lambda _success, _detail: None)
        self._condition = threading.Condition()
        self._stopping = False
        self._thread = threading.Thread(target=self._run, name="edge-http", daemon=True)
        self._thread.start()

    def close(self) -> None:
        with self._condition:
            self._stopping = True
            self._condition.notify_all()
        self._thread.join()

    def _wait_for_stop(self, seconds: float) -> bool:
        with self._condition:
            self._condition.wait_for(lambda: self._stopping, timeout=seconds)
            return self._stopping

    def _deliver(self, body: bytes) -> None:
        detail = ""
        for attempt in range(MAX_ATTEMPTS):
            try:
                status = self._send(body)
                if not is_retryable_status(status):
                    if status >= 300:
                        detail = f"HTTP {status}"
                        self._warning(f"edge payload rejected with {detail}")
                        self._result(False, detail)
                    else:
                        self._result(True, "")
                    return
                detail = f"HTTP {status}"
            except (
                urllib.error.URLError,
                http.client.HTTPException,
                TimeoutError,
                OSError,
            ) as error:
                detail = str(error)
            if attempt == MAX_ATTEMPTS - 1:
                self._warning(f"edge delivery failed after {MAX_ATTEMPTS} attempts: {detail}")
                self._result(False, detail)
                return
            if self._wait_for_stop(min(0.1 * (2**attempt), MAX_BACKOFF_SECONDS)):
                return

    def _run(self) -> None:
        raise NotImplementedError


class LatestWorker(DeliveryWorker):
    def __init__(self, send, warning, result=None) -> None:
        self._pending: bytes | None = None
        super().__init__(send, warning, result)

    def submit(self, body: bytes) -> None:
        with self._condition:
            if not self._stopping:
                self._pending = body
                self._condition.notify()

    def _run(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._stopping or self._pending is not None)
                if self._stopping:
                    return
                body, self._pending = self._pending, None
            assert body is not None
            self._deliver(body)


class QueueWorker(DeliveryWorker):
    def __init__(self, send, warning, result=None) -> None:
        self._pending: deque[bytes] = deque()
        super().__init__(send, warning, result)

    def submit(self, body: bytes) -> None:
        with self._condition:
            if not self._stopping:
                self._pending.append(body)
                self._condition.notify()

    def _run(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._stopping or self._pending)
                if self._stopping:
                    return
                body = self._pending.popleft()
            self._deliver(body)


class TelemetryBridge(Node):
    def __init__(self) -> None:
        super().__init__("telemetry_bridge")
        self.declare_parameter("robots_config", "")
        self.declare_parameter(
            "backend_url", os.getenv("TELEMETRY_BACKEND_URL", "http://localhost:8000")
        )
        self.declare_parameter("bridge_id", os.getenv("TELEMETRY_BRIDGE_ID", "edge-main"))
        config = str(self.get_parameter("robots_config").value)
        if not config:
            raise RuntimeError("robots_config parameter is required")
        self._robots = load_robot_snapshots(config)
        secret = os.getenv("EDGE_TELEMETRY_SHARED_SECRET")
        if not secret:
            raise RuntimeError("EDGE_TELEMETRY_SHARED_SECRET environment variable is required")
        backend_url = str(self.get_parameter("backend_url").value)
        opener = urllib.request.build_opener(RejectRedirectHandler())
        self._lock = threading.Lock()
        self._delivered_samples = 0
        self._failed_deliveries = 0
        self._robot_errors: dict[str, str] = {}
        self._backend_url = backend_url
        self._secret = secret
        self._opener = opener
        self._bridge_id = str(self.get_parameter("bridge_id").value)
        self._command_active = False
        self._registry_ready = False

        def sender(path: str):
            endpoint = edge_endpoint(backend_url, path)

            def send(body: bytes) -> int:
                request = urllib.request.Request(
                    endpoint,
                    body,
                    {"Content-Type": "application/json", "Authorization": "Bearer " + secret},
                )
                try:
                    with opener.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                        return response.status
                except urllib.error.HTTPError as error:
                    return error.code

            return send

        telemetry_send = sender("/internal/v1/telemetry")
        self._workers = {
            robot_id: LatestWorker(
                telemetry_send,
                self.get_logger().warning,
                lambda success, detail, key=robot_id: self._record_result(key, success, detail),
            )
            for robot_id in self._robots
        }
        self._task_worker = QueueWorker(
            sender("/internal/v1/task-updates"), self.get_logger().warning
        )
        self._health_worker = LatestWorker(
            sender("/internal/v1/bridge-health"),
            self.get_logger().warning,
            self._record_health_result,
        )
        self._queue_health()
        odom_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        state_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)
        for robot in self._robots.values():
            namespace, robot_id = robot.namespace, robot.robot_id
            self.create_subscription(
                Odometry,
                f"/{namespace}/odom",
                lambda message, key=robot_id: self._set(key, "odom", message),
                odom_qos,
            )
            for topic, field in (
                ("status", "status"),
                ("task_id", "task_id"),
                ("payload_id", "payload_id"),
            ):
                self.create_subscription(
                    String,
                    f"/{namespace}/{topic}",
                    lambda message, key=robot_id, name=field: self._set_string(key, name, message),
                    state_qos,
                )
            self.create_subscription(
                BatteryState,
                f"/{namespace}/battery_state",
                lambda message, key=robot_id: self._set_battery(key, message),
                state_qos,
            )
        task_qos = QoSProfile(
            depth=100,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(TaskState, "/fleet/task_updates", self._on_task, task_qos)
        self._apply_client = self.create_client(ApplyScenario, "/fleet/apply_scenario")
        self._task_client = self.create_client(CreateTransportTask, "/fleet/tasks/create")
        self.create_timer(0.1, self._queue_latest)
        self.create_timer(1.0, self._queue_health)
        self.create_timer(1.0, self._poll_command)

    def _poll_command(self) -> None:
        if self._command_active:
            return
        endpoint = edge_endpoint(
            self._backend_url,
            "/internal/v1/commands/next?bridge_id=" + quote(self._bridge_id, safe=""),
        )
        request = urllib.request.Request(
            endpoint, headers={"Authorization": "Bearer " + self._secret}
        )
        try:
            with self._opener.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read())
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError):
            return
        if payload is None:
            return
        operation_id = str(payload.get("operation_id", ""))
        attempt = payload.get("attempt_number")
        scenario = payload.get("payload")
        if not operation_id or not isinstance(attempt, int) or not isinstance(scenario, dict):
            self.get_logger().warning("ignoring malformed edge command")
            return
        acknowledgement = {
            "operation_id": operation_id,
            "attempt_number": attempt,
            "bridge_id": self._bridge_id,
        }
        if not self._post_command("/internal/v1/commands/ack", acknowledgement):
            return
        command_type = str(payload.get("command_type", "APPLY_SCENARIO"))
        if command_type == "CREATE_TRANSPORT_TASK":
            self._create_transport_task(scenario, acknowledgement)
            return
        if command_type != "APPLY_SCENARIO":
            self._post_result(acknowledgement, "FAILED", "unsupported command type")
            return
        if not self._apply_client.service_is_ready():
            self._post_result(acknowledgement, "FAILED", "fleet apply service unavailable")
            return
        goal = ApplyScenario.Request()
        goal.operation_id = operation_id
        goal.attempt_number = attempt
        goal.scenario_id = str(payload.get("scenario_id", ""))
        goal.layout_id = str(scenario.get("layout_id", ""))
        goal.layout_version = int(scenario.get("layout_version", 0))
        goal.route_id = str(scenario.get("route_id", ""))
        goal.robot_count = int(scenario.get("num_robots", 0))
        goal.robot_speed_mps = float(scenario.get("robot_speed_mps", 0.0))
        goal.charger_count = int(scenario.get("charger_count", 0))
        goal.demand_interval_seconds = float(scenario.get("task_arrival_interval", 0.0))
        self._command_active = True
        future = self._apply_client.call_async(goal)
        future.add_done_callback(
            lambda completed, ack=acknowledgement: self._on_apply_result(completed, ack)
        )

    def _create_transport_task(self, payload: dict, acknowledgement: dict) -> None:
        if not self._task_client.service_is_ready():
            self._post_result(acknowledgement, "FAILED", "task create service unavailable")
            return
        request = CreateTransportTask.Request()
        request.task_id = str(payload.get("task_id", ""))
        request.payload_id = str(payload.get("payload_id", ""))
        request.pickup_station_id = str(payload.get("pickup_station_id", ""))
        request.dropoff_station_id = str(payload.get("dropoff_station_id", ""))
        request.navigation_timeout_seconds = float(payload.get("navigation_timeout_seconds", 0.0))
        request.max_retries = int(payload.get("max_retries", 0))
        self._command_active = True
        future = self._task_client.call_async(request)
        future.add_done_callback(
            lambda completed, ack=acknowledgement: self._on_task_create_result(completed, ack)
        )

    def _on_task_create_result(self, future, acknowledgement: dict) -> None:
        try:
            result = future.result()
            status = "COMPLETED" if result.accepted else "FAILED"
            detail = result.message
        except Exception as error:
            status, detail = "FAILED", str(error)
        finally:
            self._command_active = False
        self._post_result(acknowledgement, status, detail)

    def _on_apply_result(self, future, acknowledgement: dict) -> None:
        try:
            result = future.result()
            status = "COMPLETED" if result.outcome == ApplyScenario.Response.COMPLETED else "FAILED"
            detail = result.detail
        except Exception as error:
            status, detail = "FAILED", str(error)
        finally:
            self._command_active = False
        self._post_result(acknowledgement, status, detail)

    def _post_result(self, acknowledgement: dict, status: str, detail: str) -> None:
        self._post_command(
            "/internal/v1/commands/result",
            {**acknowledgement, "status": status, "detail": detail},
        )

    def _post_command(self, path: str, payload: dict) -> bool:
        request = urllib.request.Request(
            edge_endpoint(self._backend_url, path),
            json.dumps(payload, separators=(",", ":")).encode(),
            {"Content-Type": "application/json", "Authorization": "Bearer " + self._secret},
        )
        try:
            with self._opener.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                return response.status < 300
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError):
            return False

    def _set(self, robot_id: str, field: str, value) -> None:
        with self._lock:
            setattr(self._robots[robot_id], field, value)

    def _set_string(self, robot_id: str, field: str, message: String) -> None:
        if field != "status" or message.data in STATUSES:
            self._set(robot_id, field, message.data)

    def _set_battery(self, robot_id: str, message: BatteryState) -> None:
        if math.isfinite(message.percentage) and 0.0 <= message.percentage <= 1.0:
            self._set(robot_id, "battery", message.percentage)
        else:
            self.get_logger().warning("ignoring BatteryState percentage outside [0, 1]")

    def _queue_latest(self) -> None:
        pending = []
        with self._lock:
            if not self._registry_ready:
                return
            for robot in self._robots.values():
                if robot.odom is not None:
                    pending.append(
                        (
                            robot.robot_id,
                            robot.odom,
                            robot.battery,
                            robot.status,
                            robot.task_id,
                            robot.payload_id,
                        )
                    )
                    robot.odom = None
        for robot_id, odom, battery, status, task_id, payload_id in pending:
            try:
                body = encode_payload(
                    robot_id, odom, battery, status, datetime.now(UTC), task_id, payload_id
                )
            except ValueError as error:
                self.get_logger().warning(f"dropping invalid telemetry: {error}")
                continue
            self._workers[robot_id].submit(body)

    def _on_task(self, message: TaskState) -> None:
        timestamp = datetime.fromtimestamp(
            message.updated_at.sec + message.updated_at.nanosec / 1_000_000_000, UTC
        )
        payload = {
            "task_id": message.task_id,
            "payload_id": message.payload_id,
            "pickup_station_id": message.pickup_station_id,
            "dropoff_station_id": message.dropoff_station_id,
            "assigned_robot_id": message.assigned_robot_id or None,
            "status": message.status,
            "attempt": message.attempt,
            "max_retries": message.max_retries,
            "message": message.message,
            "updated_at": iso_timestamp(timestamp),
        }
        self._task_worker.submit(json.dumps(payload, separators=(",", ":")).encode())

    def _record_result(self, robot_id: str, success: bool, detail: str) -> None:
        with self._lock:
            if success:
                self._delivered_samples += 1
                self._robot_errors.pop(robot_id, None)
            else:
                self._failed_deliveries += 1
                self._robot_errors[robot_id] = detail

    def _record_health_result(self, success: bool, _detail: str) -> None:
        with self._lock:
            self._registry_ready = success

    def _queue_health(self) -> None:
        with self._lock:
            last_error = (
                "; ".join(
                    f"{robot_id}: {detail}"
                    for robot_id, detail in sorted(self._robot_errors.items())
                )
                or None
            )
            payload = {
                "bridge_id": str(self.get_parameter("bridge_id").value),
                "status": "DEGRADED" if last_error else "CONNECTED",
                "robot_ids": sorted(self._robots),
                "timestamp": iso_timestamp(datetime.now(UTC)),
                "delivered_samples": self._delivered_samples,
                "failed_deliveries": self._failed_deliveries,
                "last_error": last_error,
            }
        self._health_worker.submit(json.dumps(payload, separators=(",", ":")).encode())

    def destroy_node(self):
        for worker in self._workers.values():
            worker.close()
        self._task_worker.close()
        self._health_worker.close()
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
