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
                )
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
    def test_odom_connected_tf_clock_and_authenticated_telemetry(self):
        rclpy.init()
        node = rclpy.create_node("amr_sim_smoke_test")
        odom = []
        clocks = []
        dynamic = set()
        static = set()

        def record_tf(message: TFMessage, target: set[tuple[str, str]]):
            target.update(
                (transform.header.frame_id, transform.child_frame_id)
                for transform in message.transforms
            )

        node.create_subscription(Odometry, "/amr_01/odom", odom.append, qos_profile_sensor_data)
        node.create_subscription(Clock, "/clock", clocks.append, qos_profile_sensor_data)
        node.create_subscription(
            TFMessage, "/amr_01/tf", lambda message: record_tf(message, dynamic), 10
        )
        node.create_subscription(
            TFMessage,
            "/amr_01/tf_static",
            lambda message: record_tf(message, static),
            QoSProfile(
                depth=1,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            ),
        )
        deadline = time.monotonic() + 60
        try:
            while time.monotonic() < deadline and not (
                odom
                and clocks
                and ("amr_01/odom", "amr_01/base_footprint") in dynamic
                and ("amr_01/base_footprint", "amr_01/base_link") in static
                and received.is_set()
            ):
                rclpy.spin_once(node, timeout_sec=0.1)
            assert odom
            assert clocks
            assert odom[-1].header.frame_id == "amr_01/odom"
            assert odom[-1].child_frame_id == "amr_01/base_footprint", odom[-1].child_frame_id
            assert ("amr_01/odom", "amr_01/base_footprint") in dynamic
            assert ("amr_01/base_footprint", "amr_01/base_link") in static
            assert odom[-1].header.stamp.sec <= clocks[-1].clock.sec
            parents: dict[str, set[str]] = {}
            for parent, child in dynamic | static:
                parents.setdefault(child, set()).add(parent)
            assert all(len(child_parents) == 1 for child_parents in parents.values())
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
