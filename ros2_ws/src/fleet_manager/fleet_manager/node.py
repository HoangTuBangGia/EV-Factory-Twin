import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path

import rclpy
from amr_interfaces.action import ExecuteTransportTask, NavigateToStation
from amr_interfaces.srv import ApplyScenario, SetNavigationSpeed
from amr_navigation.config import NavigationConfig, load_navigation_config
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String


@dataclass
class RobotRecord:
    robot_id: str
    namespace: str
    status: str = "OFFLINE"
    battery: float = 0.0
    x: float = math.nan
    y: float = math.nan
    task_id: str = ""


def load_robot_records(path: str | Path) -> dict[str, RobotRecord]:
    with Path(path).open(encoding="utf-8") as config_file:
        document = json.load(config_file)
    robots = document.get("robots") if isinstance(document, dict) else None
    if not isinstance(robots, list) or not robots:
        raise ValueError("robots config must contain a non-empty robots array")
    records: dict[str, RobotRecord] = {}
    namespaces: set[str] = set()
    for index, robot in enumerate(robots):
        if not isinstance(robot, dict):
            raise ValueError(f"robots[{index}] must be an object")
        robot_id, namespace = robot.get("robot_id"), robot.get("namespace")
        if not isinstance(robot_id, str) or not robot_id:
            raise ValueError(f"robots[{index}].robot_id must be a non-empty string")
        if not isinstance(namespace, str) or not namespace or "/" in namespace:
            raise ValueError(f"robots[{index}].namespace must be one ROS name segment")
        if robot_id in records or namespace in namespaces:
            raise ValueError("robot IDs and namespaces must be unique")
        records[robot_id] = RobotRecord(robot_id=robot_id, namespace=namespace)
        namespaces.add(namespace)
    return records


def select_robot(
    robots: list[RobotRecord], pickup: tuple[float, float], minimum_battery: float
) -> RobotRecord | None:
    eligible = [
        robot
        for robot in robots
        if robot.status == "IDLE"
        and not robot.task_id
        and robot.battery > minimum_battery
        and math.isfinite(robot.x)
        and math.isfinite(robot.y)
    ]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda robot: (math.hypot(robot.x - pickup[0], robot.y - pickup[1]), robot.robot_id),
    )


def select_charging_robots(
    robots: list[RobotRecord], threshold: float, capacity: int
) -> list[RobotRecord]:
    if capacity <= 0:
        return []
    return sorted(
        (
            robot
            for robot in robots
            if robot.status == "IDLE"
            and not robot.task_id
            and robot.battery <= threshold
            and math.isfinite(robot.x)
            and math.isfinite(robot.y)
        ),
        key=lambda robot: (robot.battery, robot.robot_id),
    )[:capacity]


def runtime_config_error(
    request,
    *,
    robot_count: int,
    chargers: int,
    demand: float,
    layout_id: str,
    layout_version: int,
    route_id: str,
):
    reasons = []
    if request.robot_count != robot_count:
        reasons.append(f"robot_count={request.robot_count}")
    if request.charger_count != chargers:
        reasons.append(f"charger_count={request.charger_count}")
    if not math.isclose(request.demand_interval_seconds, demand, rel_tol=0.0, abs_tol=1e-6):
        reasons.append(f"demand_interval_seconds={request.demand_interval_seconds:g}")
    if request.layout_id != layout_id:
        reasons.append(f"layout_id={request.layout_id}")
    if request.layout_version != layout_version:
        reasons.append(f"layout_version={request.layout_version}")
    if request.route_id != route_id:
        reasons.append(f"route_id={request.route_id}")
    return f"requires ROS/Gazebo relaunch: {', '.join(reasons)}" if reasons else None


class FleetManager(Node):
    def __init__(self) -> None:
        super().__init__("fleet_manager")
        self.declare_parameter("robots_config", "")
        self.declare_parameter("stations_config", "")
        self.declare_parameter("minimum_battery", 0.3)
        self.declare_parameter("charging_threshold", 0.3)
        self.declare_parameter("charging_timeout_seconds", 120.0)
        self.declare_parameter("runtime_robot_speed_mps", 1.2)
        self.declare_parameter("runtime_charger_count", 2)
        self.declare_parameter("runtime_demand_interval_seconds", 8.0)
        self.declare_parameter("runtime_layout_id", "LAYOUT-DEFAULT")
        self.declare_parameter("runtime_layout_version", 3)
        self.declare_parameter("runtime_route_id", "BATTERY_DELIVERY")
        robots_config = str(self.get_parameter("robots_config").value)
        stations_config = str(self.get_parameter("stations_config").value)
        if not robots_config or not stations_config:
            raise RuntimeError("robots_config and stations_config parameters are required")
        self._robots = load_robot_records(robots_config)
        self._navigation_config: NavigationConfig = load_navigation_config(stations_config)
        self._stations = self._navigation_config.station_positions()
        self._minimum_battery = float(self.get_parameter("minimum_battery").value)
        self._charging_threshold = float(self.get_parameter("charging_threshold").value)
        self._charging_timeout = float(self.get_parameter("charging_timeout_seconds").value)
        self._runtime_speed = float(self.get_parameter("runtime_robot_speed_mps").value)
        self._runtime_chargers = int(self.get_parameter("runtime_charger_count").value)
        self._runtime_demand = float(self.get_parameter("runtime_demand_interval_seconds").value)
        self._runtime_layout_id = str(self.get_parameter("runtime_layout_id").value)
        self._runtime_layout_version = int(self.get_parameter("runtime_layout_version").value)
        self._runtime_route_id = str(self.get_parameter("runtime_route_id").value)
        if not 0.0 < self._charging_threshold <= 1.0:
            raise RuntimeError("charging_threshold must be in (0, 1]")
        if not math.isfinite(self._charging_timeout) or self._charging_timeout <= 0.0:
            raise RuntimeError("charging_timeout_seconds must be positive and finite")
        if self._runtime_chargers < 1:
            raise RuntimeError("runtime_charger_count must be positive")
        if self._runtime_route_id not in self._navigation_config.routes:
            raise RuntimeError(f"runtime route not configured: {self._runtime_route_id}")
        if (
            self._runtime_layout_id != self._navigation_config.layout_id
            or self._runtime_layout_version != self._navigation_config.layout_version
        ):
            raise RuntimeError("runtime layout identity does not match stations_config")
        charging_stations = [
            station.station_id
            for station in self._navigation_config.stations.values()
            if station.station_type == "CHARGING_STATION"
        ]
        if not charging_stations:
            raise RuntimeError("stations_config must define a CHARGING_STATION")
        self._charger_station_id = sorted(charging_stations)[0]
        self._lock = threading.Lock()
        self._active_task_ids: set[str] = set()
        self._charging_robot_ids: set[str] = set()
        self._apply_results: dict[tuple[str, int], tuple[int, str]] = {}
        self._active_scenario_id = ""
        self._callback_group = ReentrantCallbackGroup()
        self._navigation_clients: dict[str, ActionClient] = {}
        self._speed_clients = {}

        for record in self._robots.values():
            namespace = record.namespace
            self.create_subscription(
                String,
                f"/{namespace}/status",
                lambda message, robot_id=record.robot_id: self._update_status(robot_id, message),
                10,
                callback_group=self._callback_group,
            )
            self.create_subscription(
                BatteryState,
                f"/{namespace}/battery_state",
                lambda message, robot_id=record.robot_id: self._update_battery(robot_id, message),
                10,
                callback_group=self._callback_group,
            )
            self.create_subscription(
                Odometry,
                f"/{namespace}/odom",
                lambda message, robot_id=record.robot_id: self._update_pose(robot_id, message),
                10,
                callback_group=self._callback_group,
            )
            self._navigation_clients[record.robot_id] = ActionClient(
                self,
                NavigateToStation,
                f"/{namespace}/navigate_to_station",
                callback_group=self._callback_group,
            )
            self._speed_clients[record.robot_id] = self.create_client(
                SetNavigationSpeed,
                f"/{namespace}/set_navigation_speed",
                callback_group=self._callback_group,
            )

        self._action_server = ActionServer(
            self,
            ExecuteTransportTask,
            "/fleet/execute_transport_task",
            execute_callback=self._execute,
            goal_callback=self._accept_goal,
            cancel_callback=lambda _: CancelResponse.REJECT,
            callback_group=self._callback_group,
        )
        self._apply_service = self.create_service(
            ApplyScenario,
            "/fleet/apply_scenario",
            self._apply_scenario,
            callback_group=self._callback_group,
        )
        self.create_timer(0.5, self._schedule_charging, callback_group=self._callback_group)

    def _apply_scenario(self, request, response):
        key = (request.operation_id, request.attempt_number)
        with self._lock:
            cached = self._apply_results.get(key)
            if cached is not None:
                response.outcome, response.detail = cached
                return response
            error = runtime_config_error(
                request,
                robot_count=len(self._robots),
                chargers=self._runtime_chargers,
                demand=self._runtime_demand,
                layout_id=self._runtime_layout_id,
                layout_version=self._runtime_layout_version,
                route_id=self._runtime_route_id,
            )
            if error:
                outcome = ApplyScenario.Response.REQUIRES_RELAUNCH
                detail = error
            else:
                failed = self._set_all_navigation_speeds(float(request.robot_speed_mps))
                if failed:
                    outcome = ApplyScenario.Response.FAILED
                    detail = failed
                else:
                    self._runtime_speed = float(request.robot_speed_mps)
                    self._active_scenario_id = request.scenario_id
                    outcome = ApplyScenario.Response.COMPLETED
                    detail = "scenario applied to the live ROS fleet"
            self._apply_results[key] = (outcome, detail)
        response.outcome = outcome
        response.detail = detail
        return response

    def _set_all_navigation_speeds(self, speed: float) -> str | None:
        if not math.isfinite(speed) or not 0.0 < speed <= 10.0:
            return "robot_speed_mps must be finite and in (0, 10]"
        unavailable = [
            robot_id
            for robot_id, client in self._speed_clients.items()
            if not client.wait_for_service(timeout_sec=0.5)
        ]
        if unavailable:
            return "navigation speed service unavailable: " + ", ".join(unavailable)
        requests = []
        for robot_id, client in self._speed_clients.items():
            speed_request = SetNavigationSpeed.Request()
            speed_request.linear_speed_mps = speed
            requests.append((robot_id, self._wait_future(client.call_async(speed_request), 2.0)))
        failures = [
            robot_id for robot_id, result in requests if result is None or not result.accepted
        ]
        return "navigation speed update failed: " + ", ".join(failures) if failures else None

    def _update_status(self, robot_id: str, message: String) -> None:
        with self._lock:
            robot = self._robots[robot_id]
            previous = robot.status
            robot.status = message.data
            if (
                robot_id in self._charging_robot_ids
                and previous == "CHARGING"
                and message.data == "IDLE"
            ) or (
                robot_id in self._charging_robot_ids
                and message.data in {"ERROR", "OFFLINE"}
            ):
                self._charging_robot_ids.remove(robot_id)
                robot.task_id = ""

    def _update_battery(self, robot_id: str, message: BatteryState) -> None:
        with self._lock:
            self._robots[robot_id].battery = message.percentage

    def _update_pose(self, robot_id: str, message: Odometry) -> None:
        with self._lock:
            self._robots[robot_id].x = message.pose.pose.position.x
            self._robots[robot_id].y = message.pose.pose.position.y

    def _accept_goal(self, request) -> GoalResponse:
        if (
            not request.task_id
            or request.pickup_station_id not in self._stations
            or request.dropoff_station_id not in self._stations
            or request.pickup_station_id == request.dropoff_station_id
            or not math.isfinite(request.navigation_timeout_seconds)
            or request.navigation_timeout_seconds <= 0.0
        ):
            return GoalResponse.REJECT
        with self._lock:
            if (
                request.task_id in self._active_task_ids
                or len(self._active_task_ids) >= len(self._robots)
            ):
                return GoalResponse.REJECT
            self._active_task_ids.add(request.task_id)
        return GoalResponse.ACCEPT

    def _feedback(self, goal_handle, status: str, robot_id: str, message: str) -> None:
        feedback = ExecuteTransportTask.Feedback()
        feedback.status = status
        feedback.assigned_robot_id = robot_id
        feedback.message = message
        goal_handle.publish_feedback(feedback)

    def _execute(self, goal_handle):
        result = ExecuteTransportTask.Result()
        request = goal_handle.request
        robot: RobotRecord | None = None
        try:
            with self._lock:
                robot = select_robot(
                    list(self._robots.values()),
                    self._stations[request.pickup_station_id],
                    self._minimum_battery,
                )
                if robot is not None:
                    robot.task_id = request.task_id
            if robot is None:
                goal_handle.abort()
                result.outcome = ExecuteTransportTask.Result.NO_ROBOT_AVAILABLE
                result.message = "no eligible robot available"
                return result

            result.assigned_robot_id = robot.robot_id
            self._feedback(goal_handle, "ASSIGNED", robot.robot_id, "robot assigned")
            pickup = self._navigate(robot, request.pickup_station_id, request, "")
            if pickup.outcome != NavigateToStation.Result.SUCCESS:
                return self._navigation_failure(goal_handle, result, pickup, "pickup")

            self._feedback(goal_handle, "PICKUP", robot.robot_id, "payload picked")
            self._feedback(goal_handle, "DELIVERING", robot.robot_id, "delivery started")
            route_id = self._navigation_config.route_for(
                request.pickup_station_id, request.dropoff_station_id
            )
            delivery = self._navigate(robot, request.dropoff_station_id, request, route_id)
            if delivery.outcome != NavigateToStation.Result.SUCCESS:
                return self._navigation_failure(goal_handle, result, delivery, "delivery")

            goal_handle.succeed()
            result.outcome = ExecuteTransportTask.Result.SUCCESS
            result.message = "transport completed"
            return result
        finally:
            with self._lock:
                if robot is not None and robot.task_id == request.task_id:
                    robot.task_id = ""
                self._active_task_ids.discard(request.task_id)

    def _navigate(self, robot: RobotRecord, station_id: str, request, route_id: str):
        client = self._navigation_clients[robot.robot_id]
        if not client.wait_for_server(timeout_sec=5.0):
            result = NavigateToStation.Result()
            result.outcome = NavigateToStation.Result.FAILED
            result.message = "navigation server unavailable"
            return result
        goal = NavigateToStation.Goal()
        goal.station_id = station_id
        goal.route_id = route_id
        goal.task_id = request.task_id
        goal.payload_id = request.payload_id
        goal.timeout_seconds = request.navigation_timeout_seconds
        goal_handle = self._wait_future(client.send_goal_async(goal), 5.0)
        if goal_handle is None or not goal_handle.accepted:
            result = NavigateToStation.Result()
            result.outcome = NavigateToStation.Result.FAILED
            result.message = "navigation goal rejected"
            return result
        wrapped = self._wait_future(
            goal_handle.get_result_async(), request.navigation_timeout_seconds + 5.0
        )
        if wrapped is None:
            result = NavigateToStation.Result()
            result.outcome = NavigateToStation.Result.TIMED_OUT
            result.message = "navigation result timed out"
            return result
        return wrapped.result

    def _schedule_charging(self) -> None:
        with self._lock:
            capacity = self._runtime_chargers - len(self._charging_robot_ids)
            if capacity <= 0:
                return
            candidates = select_charging_robots(
                list(self._robots.values()), self._charging_threshold, capacity
            )
            for robot in candidates:
                robot.task_id = f"__CHARGE__:{robot.robot_id}"
                self._charging_robot_ids.add(robot.robot_id)
        for robot in candidates:
            self._send_charging_goal(robot)

    def _send_charging_goal(self, robot: RobotRecord) -> None:
        client = self._navigation_clients[robot.robot_id]
        if not client.wait_for_server(timeout_sec=0.0):
            self._release_charging(robot.robot_id)
            return
        goal = NavigateToStation.Goal()
        goal.station_id = self._charger_station_id
        goal.route_id = ""
        goal.timeout_seconds = self._charging_timeout
        future = client.send_goal_async(goal)
        future.add_done_callback(
            lambda completed, robot_id=robot.robot_id: self._charging_goal_sent(
                robot_id, completed
            )
        )

    def _charging_goal_sent(self, robot_id: str, future) -> None:
        try:
            goal_handle = future.result()
        except Exception as error:
            self.get_logger().warning(f"charging goal failed for {robot_id}: {error}")
            self._release_charging(robot_id)
            return
        if goal_handle is None or not goal_handle.accepted:
            self._release_charging(robot_id)
            return
        result = goal_handle.get_result_async()
        result.add_done_callback(
            lambda completed, key=robot_id: self._charging_finished(key, completed)
        )

    def _charging_finished(self, robot_id: str, future) -> None:
        try:
            wrapped = future.result()
            succeeded = (
                wrapped is not None
                and wrapped.result.outcome == NavigateToStation.Result.SUCCESS
            )
        except Exception as error:
            self.get_logger().warning(f"charging navigation failed for {robot_id}: {error}")
            succeeded = False
        if not succeeded:
            self._release_charging(robot_id)

    def _release_charging(self, robot_id: str) -> None:
        with self._lock:
            self._charging_robot_ids.discard(robot_id)
            robot = self._robots[robot_id]
            if robot.task_id == f"__CHARGE__:{robot_id}":
                robot.task_id = ""

    @staticmethod
    def _wait_future(future, timeout: float):
        completed = threading.Event()
        future.add_done_callback(lambda _: completed.set())
        if not completed.wait(timeout):
            return None
        return future.result()

    @staticmethod
    def _navigation_failure(goal_handle, result, navigation_result, phase: str):
        goal_handle.abort()
        result.outcome = (
            ExecuteTransportTask.Result.TIMED_OUT
            if navigation_result.outcome == NavigateToStation.Result.TIMED_OUT
            else ExecuteTransportTask.Result.FAILED
        )
        result.message = f"{phase} failed: {navigation_result.message}"
        return result

    def destroy_node(self):
        self._action_server.destroy()
        self.destroy_service(self._apply_service)
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = FleetManager()
    executor = MultiThreadedExecutor(num_threads=8)
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
