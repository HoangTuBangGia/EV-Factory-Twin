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
from geometry_msgs.msg import Twist
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from nav_msgs.msg import Odometry
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
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
                launch_arguments={"gz_args": "-s -r"}.items(),
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
                    "robot_id": "AMR-01",
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
        node.create_subscription(Clock, "/clock", clocks.append, qos_profile_sensor_data)
        command_publisher = node.create_publisher(Twist, "/amr_01/cmd_vel", 10)
        deadline = time.monotonic() + 60
        try:
            while time.monotonic() < deadline and not (
                all(odom.values())
                and clocks
                and all(
                    (f"{namespace}/odom", f"{namespace}/base_footprint")
                    in dynamic[namespace]
                    and (f"{namespace}/base_footprint", f"{namespace}/base_link")
                    in static[namespace]
                    for namespace in odom
                )
                and received.is_set()
            ):
                rclpy.spin_once(node, timeout_sec=0.1)
            assert all(odom.values())
            assert clocks
            for namespace, messages in odom.items():
                assert messages[-1].header.frame_id == f"{namespace}/odom"
                assert messages[-1].child_frame_id == f"{namespace}/base_footprint"
                assert messages[-1].header.stamp.sec <= clocks[-1].clock.sec
                assert all(
                    parent.startswith(f"{namespace}/") and child.startswith(f"{namespace}/")
                    for parent, child in dynamic[namespace] | static[namespace]
                )

            parents: dict[str, set[str]] = {}
            for namespace in odom:
                for parent, child in dynamic[namespace] | static[namespace]:
                    parents.setdefault(child, set()).add(parent)
            assert all(len(child_parents) == 1 for child_parents in parents.values())

            samples_before_command = {
                namespace: len(messages) for namespace, messages in odom.items()
            }
            command = Twist()
            command.linear.x = 0.4
            command_deadline = time.monotonic() + 2.0
            while time.monotonic() < command_deadline:
                command_publisher.publish(command)
                rclpy.spin_once(node, timeout_sec=0.05)
            amr_01_after = odom["amr_01"][samples_before_command["amr_01"] :]
            amr_02_after = odom["amr_02"][samples_before_command["amr_02"] :]
            assert any(message.twist.twist.linear.x > 0.1 for message in amr_01_after)
            assert all(abs(message.twist.twist.linear.x) < 0.05 for message in amr_02_after)

            assert received.is_set()
            path, authorization, payload = requests[0]
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
            assert payload["battery"] == 100.0
            assert payload["status"] == "IDLE"
            assert payload["task_id"] is None
            assert payload["payload_id"] is None
        finally:
            node.destroy_node()
            rclpy.shutdown()


@launch_testing.post_shutdown_test()
class TestReceiverShutdown(unittest.TestCase):
    def test_stop_receiver(self):
        server.shutdown()
        server.server_close()
        server_thread.join()
