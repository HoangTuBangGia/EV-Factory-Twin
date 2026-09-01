import json
import math
import re
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

NAMESPACE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
ROBOT_ID_PATTERN = re.compile(r"^AMR-[0-9]{2,}$")
POSE_FIELDS = ("x", "y", "z", "yaw")


def load_robot_config(path: str | Path) -> list[dict[str, str | float]]:
    with Path(path).open(encoding="utf-8") as config_file:
        document = json.load(config_file)
    robots = document.get("robots") if isinstance(document, dict) else None
    if not isinstance(robots, list) or len(robots) < 2:
        raise ValueError("robots config must contain at least two robots")

    validated: list[dict[str, str | float]] = []
    robot_ids: set[str] = set()
    namespaces: set[str] = set()
    for index, robot in enumerate(robots):
        if not isinstance(robot, dict):
            raise ValueError(f"robots[{index}] must be an object")
        robot_id = robot.get("robot_id")
        namespace = robot.get("namespace")
        if not isinstance(robot_id, str) or not ROBOT_ID_PATTERN.fullmatch(robot_id):
            raise ValueError(f"robots[{index}].robot_id must match AMR-NN")
        if not isinstance(namespace, str) or not NAMESPACE_PATTERN.fullmatch(namespace):
            raise ValueError(f"robots[{index}].namespace is invalid")
        if robot_id in robot_ids:
            raise ValueError(f"duplicate robot_id: {robot_id}")
        if namespace in namespaces:
            raise ValueError(f"duplicate namespace: {namespace}")

        pose: dict[str, float] = {}
        for field in POSE_FIELDS:
            value = robot.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"robots[{index}].{field} must be numeric")
            if not math.isfinite(value):
                raise ValueError(f"robots[{index}].{field} must be finite")
            pose[field] = float(value)

        initial_battery = robot.get("initial_battery", 1.0)
        if (
            isinstance(initial_battery, bool)
            or not isinstance(initial_battery, (int, float))
            or not math.isfinite(initial_battery)
            or not 0.0 <= initial_battery <= 1.0
        ):
            raise ValueError(f"robots[{index}].initial_battery must be in [0, 1]")

        robot_ids.add(robot_id)
        namespaces.add(namespace)
        validated.append(
            {
                "robot_id": robot_id,
                "namespace": namespace,
                "initial_battery": float(initial_battery),
                **pose,
            }
        )
    return validated


def _robot_actions(context):
    config_path = LaunchConfiguration("robots_config").perform(context)
    stations_config = LaunchConfiguration("stations_config").perform(context)
    description = PathJoinSubstitution(
        [FindPackageShare("amr_description"), "urdf", "amr.urdf.xacro"]
    )
    actions = []
    for robot in load_robot_config(config_path):
        namespace = str(robot["namespace"])
        robot_description = {
            "robot_description": Command(
                ["xacro ", description, " prefix:=", namespace, "/ namespace:=", namespace]
            )
        }
        actions.extend(
            [
                Node(
                    package="robot_state_publisher",
                    executable="robot_state_publisher",
                    namespace=namespace,
                    parameters=[robot_description, {"use_sim_time": True}],
                    remappings=[("/tf", "tf"), ("/tf_static", "tf_static")],
                    output="screen",
                ),
                Node(
                    package="ros_gz_sim",
                    executable="create",
                    namespace=namespace,
                    arguments=[
                        "-name",
                        namespace,
                        "-topic",
                        "robot_description",
                        "-x",
                        str(robot["x"]),
                        "-y",
                        str(robot["y"]),
                        "-z",
                        str(robot["z"]),
                        "-Y",
                        str(robot["yaw"]),
                    ],
                    output="screen",
                ),
                Node(
                    package="ros_gz_bridge",
                    executable="parameter_bridge",
                    namespace=namespace,
                    arguments=[
                        f"/{namespace}/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
                        f"/{namespace}/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
                        f"/{namespace}/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
                    ],
                    output="screen",
                ),
                Node(
                    package="amr_navigation",
                    executable="navigation_simulator",
                    namespace=namespace,
                    parameters=[
                        {
                            "robot_id": str(robot["robot_id"]),
                            "stations_config": stations_config,
                            "initial_battery": robot["initial_battery"],
                            "linear_speed": LaunchConfiguration("runtime_robot_speed_mps"),
                            "use_sim_time": True,
                        }
                    ],
                    output="screen",
                ),
            ]
        )
    actions.extend(
        [
            Node(
                package="fleet_manager",
                executable="fleet_manager",
                parameters=[
                    {
                        "robots_config": config_path,
                        "stations_config": stations_config,
                        "runtime_robot_speed_mps": LaunchConfiguration("runtime_robot_speed_mps"),
                        "runtime_charger_count": LaunchConfiguration("runtime_charger_count"),
                        "runtime_demand_interval_seconds": LaunchConfiguration(
                            "runtime_demand_interval_seconds"
                        ),
                        "runtime_layout_id": LaunchConfiguration("runtime_layout_id"),
                        "runtime_layout_version": LaunchConfiguration("runtime_layout_version"),
                        "runtime_route_id": LaunchConfiguration("runtime_route_id"),
                        "use_sim_time": True,
                    }
                ],
                output="screen",
            ),
            Node(
                package="task_manager",
                executable="task_manager",
                parameters=[
                    {
                        "max_concurrent_tasks": len(load_robot_config(config_path)),
                        "use_sim_time": True,
                    }
                ],
                output="screen",
            ),
        ]
    )
    return actions


def generate_launch_description():
    world = PathJoinSubstitution([FindPackageShare("amr_gazebo"), "worlds", "amr_test.sdf"])
    default_config = PathJoinSubstitution([FindPackageShare("amr_gazebo"), "config", "robots.json"])
    default_stations = PathJoinSubstitution(
        [FindPackageShare("amr_navigation"), "config", "stations.json"]
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument("gz_args", default_value="-r"),
            DeclareLaunchArgument("robots_config", default_value=default_config),
            DeclareLaunchArgument("stations_config", default_value=default_stations),
            DeclareLaunchArgument("runtime_robot_speed_mps", default_value="1.2"),
            DeclareLaunchArgument("runtime_charger_count", default_value="2"),
            DeclareLaunchArgument("runtime_demand_interval_seconds", default_value="8.0"),
            DeclareLaunchArgument("runtime_layout_id", default_value="LAYOUT-DEFAULT"),
            DeclareLaunchArgument("runtime_layout_version", default_value="3"),
            DeclareLaunchArgument("runtime_route_id", default_value="BATTERY_DELIVERY"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"]
                    )
                ),
                launch_arguments={
                    "gz_args": [LaunchConfiguration("gz_args"), " ", world],
                    "on_exit_shutdown": "true",
                }.items(),
            ),
            Node(
                package="ros_gz_bridge",
                executable="parameter_bridge",
                name="clock_bridge",
                arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
                output="screen",
            ),
            OpaqueFunction(function=_robot_actions),
        ]
    )
