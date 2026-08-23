# 单板单串口模式 launch 文件
# 一块 STM32 通过一个串口 (/dev/ttyUSB0) 控制全车

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument(
            "device",
            default_value="/dev/ttyUSB0",
            description="STM32 serial device path.",
        ),
        DeclareLaunchArgument(
            "feedback_format",
            default_value="compact",
            description="Serial feedback format: compact for campusCar STM32.",
        ),
        DeclareLaunchArgument(
            "wheel_radius",
            default_value="0.0825",
            description="Wheel radius in meters.",
        ),
        DeclareLaunchArgument(
            "max_velocity",
            default_value="1.0",
            description="Hardware max velocity parameter in m/s.",
        ),
        DeclareLaunchArgument(
            "command_limit_rpm",
            default_value="50",
            description="Clamp serial steer/speed commands to this absolute RPM value.",
        ),
    ]

    device = LaunchConfiguration("device")
    feedback_format = LaunchConfiguration("feedback_format")
    wheel_radius = LaunchConfiguration("wheel_radius")
    max_velocity = LaunchConfiguration("max_velocity")
    command_limit_rpm = LaunchConfiguration("command_limit_rpm")

    # 使用单板 xacro (2 轮, 单串口)
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare("hoverboard_driver"), "urdf", "diffbot_single.urdf.xacro"]
            ),
            " ",
            "device:=", device,
            " ",
            "feedback_format:=", feedback_format,
            " ",
            "wheel_radius:=", wheel_radius,
            " ",
            "max_velocity:=", max_velocity,
            " ",
            "command_limit_rpm:=", command_limit_rpm,
        ]
    )
    robot_description = {"robot_description": robot_description_content}

    # 使用单板控制器配置 (2 关节)
    robot_controllers = PathJoinSubstitution(
        [
            FindPackageShare("hoverboard_driver"),
            "config",
            "hoverboard_controllers_single.yaml",
        ]
    )

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_description, robot_controllers],
        remappings=[
            ("/hoverboard_base_controller/cmd_vel_unstamped", "/cmd_vel"),
            ("/hoverboard_base_controller/odom", "/odom"),
        ],
        output="both",
    )
    robot_state_pub_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description],
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    robot_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["hoverboard_base_controller", "--controller-manager", "/controller_manager"],
    )

    delay_robot_controller_spawner_after_joint_state_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[robot_controller_spawner],
        )
    )

    nodes = [
        control_node,
        robot_state_pub_node,
        joint_state_broadcaster_spawner,
        delay_robot_controller_spawner_after_joint_state_broadcaster_spawner,
    ]

    return LaunchDescription(declared_arguments + nodes)
