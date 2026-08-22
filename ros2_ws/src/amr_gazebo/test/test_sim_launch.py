import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import launch
import launch_testing.actions
import pytest
import rclpy
from amr_interfaces.action import NavigateToStation
from amr_interfaces.msg import TaskState
from amr_interfaces.srv import CreateTransportTask
from geometry_msgs.msg import Twist
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage

SECRET = "launch-test-edge-secret"
requests = []
received = threading.Event()


class Receiver(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        requests.append((self.path, self.headers.get("Authorization"), json.loads(body)))
        received.set()
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):
        pass


@pytest.mark.launch_test
def generate_test_description():
    global server, server_thread
    server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return launch.LaunchDescription(
        [
            SetEnvironmentVariable("EDGE_TELEMETRY_SHARED_SECRET", SECRET),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(Path(__file__).parents[1] / "launch" / "sim.launch.py")
                ),
                launch_arguments={
                    "gz_args": "-s -r",
                    "stations_config": str(Path(__file__).parent / "fixtures" / "stations.json"),
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [
                            FindPackageShare("telemetry_bridge"),
                            "launch",
                            "telemetry_bridge.launch.py",
                        ]
                    )
                ),
                launch_arguments={
                    "backend_url": f"http://127.0.0.1:{server.server_port}",
                    "robots_config": str(Path(__file__).parents[1] / "config" / "robots.json"),
                }.items(),
            ),
            launch_testing.actions.ReadyToTest(),
        ]
    )


class TestSimRuntime(unittest.TestCase):
    def test_two_robots_have_isolated_odom_cmd_vel_tf_and_telemetry(self):
        rclpy.init()
        node = rclpy.create_node("amr_sim_smoke_test")
        odom = {"amr_01": [], "amr_02": []}
        clocks = []
        dynamic = {"amr_01": set(), "amr_02": set()}
        static = {"amr_01": set(), "amr_02": set()}
        batteries = {"amr_01": [], "amr_02": []}
        statuses = {"amr_01": [], "amr_02": []}
        task_ids = {"amr_01": [], "amr_02": []}
        payload_ids = {"amr_01": [], "amr_02": []}
        task_updates = []

        def record_tf(message: TFMessage, target: set[tuple[str, str]]):
            target.update(
                (transform.header.frame_id, transform.child_frame_id)
                for transform in message.transforms
            )

        for namespace in odom:
            node.create_subscription(
                Odometry,
                f"/{namespace}/odom",
                odom[namespace].append,
                qos_profile_sensor_data,
            )
            node.create_subscription(
                TFMessage,
                f"/{namespace}/tf",
                lambda message, ns=namespace: record_tf(message, dynamic[ns]),
                10,
            )
            node.create_subscription(
                TFMessage,
                f"/{namespace}/tf_static",
                lambda message, ns=namespace: record_tf(message, static[ns]),
                QoSProfile(
                    depth=1,
                    durability=DurabilityPolicy.TRANSIENT_LOCAL,
                    reliability=ReliabilityPolicy.RELIABLE,
                ),
            )
            node.create_subscription(
                BatteryState,
                f"/{namespace}/battery_state",
                batteries[namespace].append,
                10,
            )
            node.create_subscription(
                String,
                f"/{namespace}/status",
                lambda message, ns=namespace: statuses[ns].append(message.data),
                10,
            )
            node.create_subscription(
                String,
                f"/{namespace}/task_id",
                lambda message, ns=namespace: task_ids[ns].append(message.data),
                10,
            )
            node.create_subscription(
                String,
                f"/{namespace}/payload_id",
                lambda message, ns=namespace: payload_ids[ns].append(message.data),
                10,
            )
        node.create_subscription(Clock, "/clock", clocks.append, qos_profile_sensor_data)
        node.create_subscription(TaskState, "/fleet/task_updates", task_updates.append, 100)
        command_publisher = node.create_publisher(Twist, "/amr_01/cmd_vel", 10)
        deadline = time.monotonic() + 60
        try:
            while time.monotonic() < deadline and not (
                all(odom.values())
                and all(batteries.values())
                and all(statuses.values())
                and clocks
                and all(
                    (f"{namespace}/odom", f"{namespace}/base_footprint") in dynamic[namespace]
                    and (f"{namespace}/base_footprint", f"{namespace}/base_link")
                    in static[namespace]
                    for namespace in odom
                )
                and received.is_set()
            ):
                rclpy.spin_once(node, timeout_sec=0.1)
            assert all(odom.values())
            assert all(batteries.values())
            assert all(statuses.values())
            assert clocks
            for namespace, messages in odom.items():
                assert messages[-1].header.frame_id == f"{namespace}/odom"
                assert messages[-1].child_frame_id == f"{namespace}/base_footprint"
                assert messages[-1].header.stamp.sec <= clocks[-1].clock.sec + 1
                assert all(
                    parent.startswith(f"{namespace}/") and child.startswith(f"{namespace}/")
                    for parent, child in dynamic[namespace] | static[namespace]
                )

            parents: dict[str, set[str]] = {}
            for namespace in odom:
                for parent, child in dynamic[namespace] | static[namespace]:
                    parents.setdefault(child, set()).add(parent)
            assert all(len(child_parents) == 1 for child_parents in parents.values())

            create_task = node.create_client(CreateTransportTask, "/fleet/tasks/create")
            assert create_task.wait_for_service(timeout_sec=5.0)
            request = CreateTransportTask.Request()
            request.task_id = "TASK-FLEET-0001"
            request.payload_id = "BP-FLEET-0001"
            request.pickup_station_id = "BATTERY_BUFFER"
            request.dropoff_station_id = "MARRIAGE_STATION"
            request.navigation_timeout_seconds = 20.0
            response_future = create_task.call_async(request)
            rclpy.spin_until_future_complete(node, response_future, timeout_sec=5.0)
            response = response_future.result()
            assert response is not None and response.accepted

            task_deadline = time.monotonic() + 60.0
            while time.monotonic() < task_deadline and not any(
                update.task_id == request.task_id and update.status == "COMPLETED"
                for update in task_updates
            ):
                rclpy.spin_once(node, timeout_sec=0.05)
            lifecycle = []
            for update in task_updates:
                if update.task_id == request.task_id and (
                    not lifecycle or lifecycle[-1] != update.status
                ):
                    lifecycle.append(update.status)
            task_trace = [
                (update.status, update.message, update.attempt)
                for update in task_updates
                if update.task_id == request.task_id
            ]
            assert lifecycle == [
                "QUEUED",
                "ASSIGNED",
                "PICKUP",
                "DELIVERING",
                "COMPLETED",
            ], task_trace
            assigned = [
                update.assigned_robot_id
                for update in task_updates
                if update.task_id == request.task_id and update.status == "ASSIGNED"
            ]
            assert len(assigned) == 1 and assigned[0] in {"AMR-01", "AMR-02"}, assigned

            amr_01_action = ActionClient(node, NavigateToStation, "/amr_01/navigate_to_station")
            amr_02_action = ActionClient(node, NavigateToStation, "/amr_02/navigate_to_station")
            assert amr_01_action.wait_for_server(timeout_sec=5.0)
            assert amr_02_action.wait_for_server(timeout_sec=5.0)

            state_override = node.create_publisher(String, "/amr_02/state_override", 10)
            charge_deadline = time.monotonic() + 1.0
            while time.monotonic() < charge_deadline:
                state_override.publish(String(data="CHARGING"))
                rclpy.spin_once(node, timeout_sec=0.05)
            assert "CHARGING" in statuses["amr_02"]
            assert max(message.percentage for message in batteries["amr_02"]) > 0.6

            timeout_goal = NavigateToStation.Goal()
            timeout_goal.station_id = "CHARGING_STATION"
            timeout_goal.task_id = "TASK-0001"
            timeout_goal.payload_id = "BP-0001"
            timeout_goal.timeout_seconds = 0.2
            timeout_result = self._send_goal(node, amr_01_action, timeout_goal)
            assert timeout_result.outcome == NavigateToStation.Result.TIMED_OUT

            failed_goal = NavigateToStation.Goal()
            failed_goal.station_id = "UNKNOWN_STATION"
            failed_goal.timeout_seconds = 1.0
            failed_result = self._send_goal(node, amr_02_action, failed_goal)
            assert failed_result.outcome == NavigateToStation.Result.FAILED

            samples_before_command = {
                namespace: len(messages) for namespace, messages in odom.items()
            }
            command = Twist()
            command.linear.x = 0.4
            command_deadline = time.monotonic() + 1.0
            while time.monotonic() < command_deadline:
                command_publisher.publish(command)
                rclpy.spin_once(node, timeout_sec=0.05)
            amr_01_after = odom["amr_01"][samples_before_command["amr_01"] :]
            amr_02_after = odom["amr_02"][samples_before_command["amr_02"] :]
            assert any(message.twist.twist.linear.x > 0.1 for message in amr_01_after)
            assert all(abs(message.twist.twist.linear.x) < 0.05 for message in amr_02_after)

            assert received.is_set()
            telemetry_requests = [item for item in requests if item[0] == "/internal/v1/telemetry"]
            assert {item[2]["robot_id"] for item in telemetry_requests} == {"AMR-01", "AMR-02"}
            assert any(item[2]["task_id"] == request.task_id for item in telemetry_requests)
            assert any(item[2]["payload_id"] == request.payload_id for item in telemetry_requests)
            assert any(item[0] == "/internal/v1/task-updates" for item in requests)
            assert any(item[0] == "/internal/v1/bridge-health" for item in requests)
            path, authorization, payload = next(
                item for item in telemetry_requests if item[2]["robot_id"] == "AMR-01"
            )
            assert path == "/internal/v1/telemetry"
            assert authorization == f"Bearer {SECRET}"
            assert set(payload) == {
                "timestamp",
                "robot_id",
                "pose",
                "velocity",
                "battery",
                "status",
                "task_id",
                "payload_id",
            }
            assert payload["timestamp"].endswith("Z")
            assert payload["robot_id"] == "AMR-01"
            assert set(payload["pose"]) == {"x", "y", "yaw"}
            assert set(payload["velocity"]) == {"linear", "angular"}
            assert all(isinstance(value, (int, float)) for value in payload["pose"].values())
            assert all(isinstance(value, (int, float)) for value in payload["velocity"].values())
            assert 0.0 <= payload["battery"] <= 100.0
            assert payload["status"] == "IDLE"
            assert payload["task_id"] is None
            assert payload["payload_id"] is None
        finally:
            node.destroy_node()
            rclpy.shutdown()

    @staticmethod
    def _send_goal(node, action_client, goal):
        goal_future = action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(node, goal_future, timeout_sec=5.0)
        goal_handle = goal_future.result()
        assert goal_handle is not None and goal_handle.accepted
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(node, result_future, timeout_sec=15.0)
        wrapped_result = result_future.result()
        assert wrapped_result is not None
        return wrapped_result.result


@launch_testing.post_shutdown_test()
class TestReceiverShutdown(unittest.TestCase):
    def test_stop_receiver(self):
        server.shutdown()
        server.server_close()
        server_thread.join()
