from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    namespace = LaunchConfiguration("namespace")
    robot_name = LaunchConfiguration("robot_name")
    world = PathJoinSubstitution([FindPackageShare("amr_gazebo"), "worlds", "amr_test.sdf"])
    description = PathJoinSubstitution(
        [FindPackageShare("amr_description"), "urdf", "amr.urdf.xacro"]
    )
    robot_description = {
        "robot_description": Command(
            ["xacro ", description, " prefix:=", namespace, "/ namespace:=", namespace]
        )
    }
    return LaunchDescription(
        [
            DeclareLaunchArgument("namespace", default_value="amr_01"),
            DeclareLaunchArgument("robot_name", default_value="amr_01"),
            DeclareLaunchArgument("gz_args", default_value="-r"),
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
                arguments=[
                    "-name",
                    robot_name,
                    "-topic",
                    "robot_description",
                    "-x",
                    "0",
                    "-y",
                    "0",
                    "-z",
                    "0.2",
                ],
                namespace=namespace,
                output="screen",
            ),
            Node(
                package="ros_gz_bridge",
                executable="parameter_bridge",
                arguments=[
                    "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
                    ["/", namespace, "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist"],
                    ["/", namespace, "/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry"],
                    ["/", namespace, "/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V"],
                ],
                output="screen",
            ),
        ]
    )
