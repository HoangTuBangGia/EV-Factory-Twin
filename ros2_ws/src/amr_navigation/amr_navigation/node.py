import math
import threading
import time

import rclpy
from amr_interfaces.action import NavigateToStation
from amr_interfaces.srv import SetNavigationSpeed
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String

from amr_navigation.config import load_navigation_config

STATUSES = {"IDLE", "MOVING", "PICKING", "DELIVERING", "CHARGING", "ERROR", "OFFLINE"}
MOVING_STATUSES = {"MOVING", "DELIVERING"}


def yaw_from_odometry(message: Odometry) -> float:
    orientation = message.pose.pose.orientation
    return math.atan2(
        2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
        1.0 - 2.0 * (orientation.y**2 + orientation.z**2),
    )


def normalize_angle(value: float) -> float:
    return math.atan2(math.sin(value), math.cos(value))


def next_battery(
    battery: float,
    status: str,
    dt: float,
    moving_drain: float,
    charging_gain: float,
) -> float:
    if status in MOVING_STATUSES:
        return max(0.0, battery - moving_drain * dt)
    if status == "CHARGING":
        return min(1.0, battery + charging_gain * dt)
    return battery


def navigation_speed_error(speed: float) -> str | None:
    if not math.isfinite(speed) or not 0.0 < speed <= 10.0:
        return "linear_speed_mps must be finite and in (0, 10]"
    return None


class NavigationSimulator(Node):
    def __init__(self) -> None:
        super().__init__("navigation_simulator")
        self.declare_parameter("robot_id", "AMR-01")
        self.declare_parameter("stations_config", "")
        self.declare_parameter("linear_speed", 1.0)
        self.declare_parameter("angular_speed", 1.5)
        self.declare_parameter("arrival_tolerance", 0.15)
        self.declare_parameter("initial_battery", 1.0)
        self.declare_parameter("moving_drain_per_second", 0.005)
        self.declare_parameter("charging_gain_per_second", 0.05)
        self.declare_parameter("charge_target", 0.9)

        stations_config = str(self.get_parameter("stations_config").value)
        if not stations_config:
            raise RuntimeError("stations_config parameter is required")
        self._config = load_navigation_config(stations_config)
        self._stations = self._config.station_positions()
        self._linear_speed = float(self.get_parameter("linear_speed").value)
        self._angular_speed = float(self.get_parameter("angular_speed").value)
        self._arrival_tolerance = float(self.get_parameter("arrival_tolerance").value)
        self._moving_drain = float(self.get_parameter("moving_drain_per_second").value)
        self._charging_gain = float(self.get_parameter("charging_gain_per_second").value)
        self._charge_target = float(self.get_parameter("charge_target").value)

        self._lock = threading.Lock()
        self._odom: Odometry | None = None
        self._status = "IDLE"
        self._task_id = ""
        self._payload_id = ""
        self._battery = float(self.get_parameter("initial_battery").value)
        self._active_goal = False
        self._last_state_time = self.get_clock().now()

        callback_group = ReentrantCallbackGroup()
        self._cmd_vel = self.create_publisher(Twist, "cmd_vel", 10)
        self._battery_publisher = self.create_publisher(BatteryState, "battery_state", 10)
        self._status_publisher = self.create_publisher(String, "status", 10)
        self._task_publisher = self.create_publisher(String, "task_id", 10)
        self._payload_publisher = self.create_publisher(String, "payload_id", 10)
        self.create_subscription(Odometry, "odom", self._on_odom, 10)
        self.create_subscription(String, "state_override", self._on_state_override, 10)
        self.create_timer(0.1, self._publish_state, callback_group=callback_group)
        self._action_server = ActionServer(
            self,
            NavigateToStation,
            "navigate_to_station",
            execute_callback=self._execute,
            goal_callback=self._accept_goal,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=callback_group,
        )
        self._speed_service = self.create_service(
            SetNavigationSpeed,
            "set_navigation_speed",
            self._set_navigation_speed,
            callback_group=callback_group,
        )

    def _set_navigation_speed(self, request, response):
        speed = float(request.linear_speed_mps)
        error = navigation_speed_error(speed)
        if error:
            response.accepted = False
            response.detail = error
            return response
        with self._lock:
            self._linear_speed = speed
        response.accepted = True
        response.detail = f"navigation speed set to {speed:g} m/s"
        return response

    def _on_odom(self, message: Odometry) -> None:
        with self._lock:
            self._odom = message

    def _on_state_override(self, message: String) -> None:
        if message.data not in STATUSES:
            self.get_logger().warning(f"ignoring invalid state override: {message.data}")
            return
        with self._lock:
            self._status = message.data
        if message.data in {"ERROR", "OFFLINE"}:
            self._stop()

    def _accept_goal(self, request) -> GoalResponse:
        if not math.isfinite(request.timeout_seconds) or request.timeout_seconds <= 0.0:
            return GoalResponse.REJECT
        with self._lock:
            if self._active_goal:
                return GoalResponse.REJECT
            self._active_goal = True
        return GoalResponse.ACCEPT

    def _world_pose(self, odom: Odometry) -> tuple[float, float, float]:
        position = odom.pose.pose.position
        return position.x, position.y, yaw_from_odometry(odom)

    def _execute(self, goal_handle):
        result = NavigateToStation.Result()
        request = goal_handle.request
        station = self._config.stations.get(request.station_id)
        if station is None:
            return self._finish_failed(
                goal_handle, result, f"unknown station: {request.station_id}"
            )

        started = self.get_clock().now()
        last_distance = math.inf
        path: tuple[tuple[float, float], ...] | None = None
        waypoint_index = 0
        with self._lock:
            self._task_id = request.task_id
            self._payload_id = request.payload_id
            self._status = (
                "DELIVERING"
                if station.arrival_status != "PICKING" and request.payload_id
                else "MOVING"
            )
        try:
            while rclpy.ok():
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    result.outcome = NavigateToStation.Result.FAILED
                    result.message = "navigation canceled"
                    return result
                elapsed = (self.get_clock().now() - started).nanoseconds / 1_000_000_000
                if elapsed >= request.timeout_seconds:
                    with self._lock:
                        self._status = "ERROR"
                    goal_handle.abort()
                    result.outcome = NavigateToStation.Result.TIMED_OUT
                    result.message = f"navigation timed out; distance_remaining={last_distance:.3f}"
                    return result
                with self._lock:
                    odom = self._odom
                    status = self._status
                    battery = self._battery
                if status in {"ERROR", "OFFLINE"}:
                    return self._finish_failed(goal_handle, result, f"robot entered {status}")
                if odom is None:
                    time.sleep(0.05)
                    continue

                x, y, yaw = self._world_pose(odom)
                if path is None:
                    try:
                        path = self._config.path_to(
                            (x, y), request.station_id, request.route_id
                        )
                    except ValueError as error:
                        return self._finish_failed(goal_handle, result, str(error))
                target = path[waypoint_index]
                dx, dy = target[0] - x, target[1] - y
                distance = math.hypot(dx, dy)
                last_distance = distance + sum(
                    math.hypot(end[0] - start[0], end[1] - start[1])
                    for start, end in zip(
                        path[waypoint_index:],
                        path[waypoint_index + 1 :],
                        strict=False,
                    )
                )
                feedback = NavigateToStation.Feedback()
                feedback.distance_remaining = last_distance
                feedback.robot_status = status
                feedback.battery_percent = battery * 100.0
                goal_handle.publish_feedback(feedback)
                if distance <= self._arrival_tolerance:
                    waypoint_index += 1
                    if waypoint_index < len(path):
                        continue
                    self._stop()
                    with self._lock:
                        self._status = station.arrival_status
                        if station.arrival_status != "PICKING":
                            self._task_id = ""
                            self._payload_id = ""
                    goal_handle.succeed()
                    result.outcome = NavigateToStation.Result.SUCCESS
                    result.message = f"arrived at {request.station_id}"
                    return result

                heading_error = normalize_angle(math.atan2(dy, dx) - yaw)
                command = Twist()
                command.angular.z = max(
                    -self._angular_speed, min(self._angular_speed, 2.0 * heading_error)
                )
                if abs(heading_error) < 0.35:
                    command.linear.x = min(self._linear_speed, distance)
                self._cmd_vel.publish(command)
                time.sleep(0.05)
        finally:
            self._stop()
            with self._lock:
                self._active_goal = False

    def _finish_failed(self, goal_handle, result, message: str):
        self._stop()
        with self._lock:
            self._status = "ERROR"
            self._active_goal = False
        goal_handle.abort()
        result.outcome = NavigateToStation.Result.FAILED
        result.message = message
        return result

    def _stop(self) -> None:
        self._cmd_vel.publish(Twist())

    def _publish_state(self) -> None:
        now = self.get_clock().now()
        dt = max(0.0, (now - self._last_state_time).nanoseconds / 1_000_000_000)
        self._last_state_time = now
        with self._lock:
            self._battery = next_battery(
                self._battery,
                self._status,
                dt,
                self._moving_drain,
                self._charging_gain,
            )
            if self._status == "CHARGING" and self._battery >= self._charge_target:
                self._status = "IDLE"
            status, task_id, payload_id, battery = (
                self._status,
                self._task_id,
                self._payload_id,
                self._battery,
            )
        battery_message = BatteryState()
        battery_message.header.stamp = now.to_msg()
        battery_message.percentage = battery
        self._battery_publisher.publish(battery_message)
        self._status_publisher.publish(String(data=status))
        self._task_publisher.publish(String(data=task_id))
        self._payload_publisher.publish(String(data=payload_id))

    def destroy_node(self):
        self._action_server.destroy()
        self.destroy_service(self._speed_service)
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = NavigationSimulator()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
