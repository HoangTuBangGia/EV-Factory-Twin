import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path

import rclpy
from amr_interfaces.action import ExecuteTransportTask, NavigateToStation
from amr_interfaces.srv import ApplyScenario
from amr_navigation.node import load_stations as load_station_positions
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


def runtime_config_error(request, *, robot_count: int, speed: float, chargers: int, demand: float):
    if request.robot_count != robot_count:
        return f"robot_count={request.robot_count} requires Gazebo relaunch"
    if not math.isclose(request.robot_speed_mps, speed, rel_tol=0.0, abs_tol=1e-6):
        return f"robot_speed_mps={request.robot_speed_mps} requires Gazebo relaunch"
    if request.charger_count != chargers:
        return f"charger_count={request.charger_count} requires Gazebo relaunch"
    if not math.isclose(request.demand_interval_seconds, demand, rel_tol=0.0, abs_tol=1e-6):
        return f"demand_interval_seconds={request.demand_interval_seconds} requires relaunch"
    if not request.layout_id or not request.route_id:
        return "invalid runtime scenario configuration"
    return None


class FleetManager(Node):
    def __init__(self) -> None:
        super().__init__("fleet_manager")
        self.declare_parameter("robots_config", "")
        self.declare_parameter("stations_config", "")
        self.declare_parameter("minimum_battery", 0.2)
        self.declare_parameter("runtime_robot_speed_mps", 1.0)
        self.declare_parameter("runtime_charger_count", 1)
        self.declare_parameter("runtime_demand_interval_seconds", 8.0)
        robots_config = str(self.get_parameter("robots_config").value)
        stations_config = str(self.get_parameter("stations_config").value)
        if not robots_config or not stations_config:
            raise RuntimeError("robots_config and stations_config parameters are required")
        self._robots = load_robot_records(robots_config)
        self._stations = load_station_positions(stations_config)
        self._minimum_battery = float(self.get_parameter("minimum_battery").value)
        self._runtime_speed = float(self.get_parameter("runtime_robot_speed_mps").value)
        self._runtime_chargers = int(self.get_parameter("runtime_charger_count").value)
        self._runtime_demand = float(self.get_parameter("runtime_demand_interval_seconds").value)
        self._lock = threading.Lock()
        self._active = False
        self._apply_results: dict[tuple[str, int], tuple[int, str]] = {}
        self._active_scenario_id = ""
        self._callback_group = ReentrantCallbackGroup()
        self._navigation_clients: dict[str, ActionClient] = {}

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
                speed=self._runtime_speed,
                chargers=self._runtime_chargers,
                demand=self._runtime_demand,
            )
            if error:
                outcome = ApplyScenario.Response.FAILED
                detail = error
            else:
                self._active_scenario_id = request.scenario_id
                outcome = ApplyScenario.Response.COMPLETED
                detail = "scenario configuration accepted by fleet simulation"
            self._apply_results[key] = (outcome, detail)
        response.outcome = outcome
        response.detail = detail
        return response

    def _update_status(self, robot_id: str, message: String) -> None:
        with self._lock:
            self._robots[robot_id].status = message.data

    def _update_battery(self, robot_id: str, message: BatteryState) -> None:
        with self._lock:
            self._robots[robot_id].battery = message.percentage

    def _update_pose(self, robot_id: str, message: Odometry) -> None:
        with self._lock:
            self._robots[robot_id].x = message.pose.pose.position.x
            self._robots[robot_id].y = message.pose.pose.position.y

    def _accept_goal(self, request) -> GoalResponse:
        if (
            request.pickup_station_id not in self._stations
            or request.dropoff_station_id not in self._stations
            or not math.isfinite(request.navigation_timeout_seconds)
            or request.navigation_timeout_seconds <= 0.0
        ):
            return GoalResponse.REJECT
        with self._lock:
            if self._active:
                return GoalResponse.REJECT
            self._active = True
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
            pickup = self._navigate(robot, request.pickup_station_id, request)
            if pickup.outcome != NavigateToStation.Result.SUCCESS:
                return self._navigation_failure(goal_handle, result, pickup, "pickup")

            self._feedback(goal_handle, "PICKUP", robot.robot_id, "payload picked")
            self._feedback(goal_handle, "DELIVERING", robot.robot_id, "delivery started")
            delivery = self._navigate(robot, request.dropoff_station_id, request)
            if delivery.outcome != NavigateToStation.Result.SUCCESS:
                return self._navigation_failure(goal_handle, result, delivery, "delivery")

            goal_handle.succeed()
            result.outcome = ExecuteTransportTask.Result.SUCCESS
            result.message = "transport completed"
            return result
        finally:
            with self._lock:
                if robot is not None:
                    robot.task_id = ""
                self._active = False

    def _navigate(self, robot: RobotRecord, station_id: str, request):
        client = self._navigation_clients[robot.robot_id]
        if not client.wait_for_server(timeout_sec=5.0):
            result = NavigateToStation.Result()
            result.outcome = NavigateToStation.Result.FAILED
            result.message = "navigation server unavailable"
            return result
        goal = NavigateToStation.Goal()
        goal.station_id = station_id
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
