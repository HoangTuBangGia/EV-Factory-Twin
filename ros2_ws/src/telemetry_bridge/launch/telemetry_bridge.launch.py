from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    namespace = LaunchConfiguration("namespace")
    return LaunchDescription(
        [
            DeclareLaunchArgument("namespace", default_value="amr_01"),
            DeclareLaunchArgument("robot_id", default_value="AMR-01"),
            DeclareLaunchArgument("backend_url", default_value="http://localhost:8000"),
            Node(
                package="telemetry_bridge",
                executable="telemetry_bridge",
                namespace=namespace,
                parameters=[
                    {
                        "robot_id": LaunchConfiguration("robot_id"),
                        "backend_url": LaunchConfiguration("backend_url"),
                    }
                ],
                output="screen",
            ),
        ]
    )
