from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("robots_config"),
            DeclareLaunchArgument("bridge_id", default_value="edge-main"),
            DeclareLaunchArgument("backend_url", default_value="http://localhost:8000"),
            Node(
                package="telemetry_bridge",
                executable="telemetry_bridge",
                parameters=[
                    {
                        "robots_config": LaunchConfiguration("robots_config"),
                        "bridge_id": LaunchConfiguration("bridge_id"),
                        "backend_url": LaunchConfiguration("backend_url"),
                    }
                ],
                output="screen",
            ),
        ]
    )
