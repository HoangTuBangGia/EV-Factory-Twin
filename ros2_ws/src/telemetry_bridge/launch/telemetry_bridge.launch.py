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
            DeclareLaunchArgument("runtime_layout_id", default_value="LAYOUT-DEFAULT"),
            DeclareLaunchArgument("runtime_layout_version", default_value="3"),
            DeclareLaunchArgument("runtime_route_id", default_value="BATTERY_DELIVERY"),
            DeclareLaunchArgument("runtime_robot_speed_mps", default_value="1.0"),
            DeclareLaunchArgument("runtime_charger_count", default_value="1"),
            DeclareLaunchArgument("runtime_demand_interval_seconds", default_value="8.0"),
            Node(
                package="telemetry_bridge",
                executable="telemetry_bridge",
                parameters=[
                    {
                        "robots_config": LaunchConfiguration("robots_config"),
                        "bridge_id": LaunchConfiguration("bridge_id"),
                        "backend_url": LaunchConfiguration("backend_url"),
                        "runtime_layout_id": LaunchConfiguration("runtime_layout_id"),
                        "runtime_layout_version": LaunchConfiguration("runtime_layout_version"),
                        "runtime_route_id": LaunchConfiguration("runtime_route_id"),
                        "runtime_robot_speed_mps": LaunchConfiguration("runtime_robot_speed_mps"),
                        "runtime_charger_count": LaunchConfiguration("runtime_charger_count"),
                        "runtime_demand_interval_seconds": LaunchConfiguration(
                            "runtime_demand_interval_seconds"
                        ),
                    }
                ],
                output="screen",
            ),
        ]
    )
