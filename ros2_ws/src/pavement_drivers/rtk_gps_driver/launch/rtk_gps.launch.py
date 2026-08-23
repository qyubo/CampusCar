from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("serial_port", default_value="auto"),
            DeclareLaunchArgument("baudrate", default_value="115200"),
            DeclareLaunchArgument("ntrip_enabled", default_value="false"),
            DeclareLaunchArgument("ntrip_server", default_value=""),
            DeclareLaunchArgument("ntrip_port", default_value="2101"),
            DeclareLaunchArgument("ntrip_mountpoint", default_value=""),
            DeclareLaunchArgument("ntrip_user", default_value=""),
            DeclareLaunchArgument("ntrip_password", default_value=""),
            Node(
                package="rtk_gps_driver",
                executable="rtk_gps_node",
                name="rtk_gps_node",
                output="screen",
                parameters=[
                    {
                        "serial_port": LaunchConfiguration("serial_port"),
                        "baudrate": ParameterValue(
                            LaunchConfiguration("baudrate"), value_type=int
                        ),
                        "ntrip_enabled": ParameterValue(
                            LaunchConfiguration("ntrip_enabled"), value_type=bool
                        ),
                        "ntrip_server": LaunchConfiguration("ntrip_server"),
                        "ntrip_port": ParameterValue(
                            LaunchConfiguration("ntrip_port"), value_type=int
                        ),
                        "ntrip_mountpoint": LaunchConfiguration("ntrip_mountpoint"),
                        "ntrip_user": LaunchConfiguration("ntrip_user"),
                        "ntrip_password": LaunchConfiguration("ntrip_password"),
                    }
                ],
            ),
        ]
    )
