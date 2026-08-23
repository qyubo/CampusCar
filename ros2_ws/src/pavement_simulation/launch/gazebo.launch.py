"""CyberLuban Gazebo 仿真启动文件

启动:
  1. Gazebo Fortress (Ignition Gazebo 6) - headless 或 GUI 模式
  2. Spawn 巡检机器人模型 (rover)
  3. ros_gz_bridge 桥接 Gazebo Transport <-> ROS2 话题
  4. (可选) 静态 TF 发布

用法:
  ros2 launch pavement_simulation gazebo.launch.py                    # GUI 模式
  ros2 launch pavement_simulation gazebo.launch.py headless:=true     # 无头模式
  ros2 launch pavement_simulation gazebo.launch.py world:=road_inspection.sdf
"""
import os
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess,
    RegisterEventHandler, SetEnvironmentVariable, GroupAction
)
from launch.event_handlers import OnProcessStart
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # ---- 参数 ----
    headless_arg = DeclareLaunchArgument(
        'headless', default_value='false',
        description='true=无头模式(无GUI), false=GUI模式')

    world_arg = DeclareLaunchArgument(
        'world', default_value='road_inspection.sdf',
        description='世界 SDF 文件名')

    bridge_config_arg = DeclareLaunchArgument(
        'bridge_config', default_value='bridge.yaml',
        description='ros_gz_bridge 配置文件名')

    robot_name_arg = DeclareLaunchArgument(
        'robot_name', default_value='rover',
        description='机器人模型名称')

    x_arg = DeclareLaunchArgument('x', default_value='0.0',
                                   description='机器人初始 X 坐标')
    y_arg = DeclareLaunchArgument('y', default_value='0.0',
                                   description='机器人初始 Y 坐标')
    z_arg = DeclareLaunchArgument('z', default_value='0.15',
                                   description='机器人初始 Z 坐标')

    headless = LaunchConfiguration('headless')
    world_file = LaunchConfiguration('world')
    bridge_file = LaunchConfiguration('bridge_config')
    robot_name = LaunchConfiguration('robot_name')
    x = LaunchConfiguration('x')
    y = LaunchConfiguration('y')
    z = LaunchConfiguration('z')

    pkg_share = get_package_share_directory('pavement_simulation')
    world_path = os.path.join(pkg_share, 'worlds', 'road_inspection.sdf')
    bridge_path = os.path.join(pkg_share, 'config', 'bridge.yaml')
    model_path = os.path.join(pkg_share, 'models', 'rover', 'model.sdf')

    # ---- 环境变量: 解决 ~/.ros/log 只读问题 ----
    env_setup = GroupAction([
        SetEnvironmentVariable(
            name='ROS_LOG_DIR',
            value=[os.path.join(os.environ.get('HOME', '/tmp'), '.ros/log_gz')]),
        SetEnvironmentVariable(
            name='RCL_LOG_DIR',
            value=[os.path.join(os.environ.get('HOME', '/tmp'), '.ros/log_gz')]),
        SetEnvironmentVariable(
            name='ROS_HOME',
            value=[os.path.join(os.environ.get('HOME', '/tmp'), '.ros')]),
        # 让 Gazebo 找到模型
        SetEnvironmentVariable(
            name='IGN_GAZEBO_RESOURCE_PATH',
            value=[os.path.join(pkg_share, 'models'), ':',
                   os.environ.get('IGN_GAZEBO_RESOURCE_PATH', '')]),
        SetEnvironmentVariable(
            name='GZ_SIM_RESOURCE_PATH',
            value=[os.path.join(pkg_share, 'models'), ':',
                   os.environ.get('GZ_SIM_RESOURCE_PATH', '')]),
    ])

    # ---- 1. Gazebo Fortress ----
    gz_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'),
                         'launch', 'gz_sim.launch.py')),
        launch_arguments={
            'gz_args': Command([
                'echo "',
                world_path,
                '" && echo "', headless,
                '" | grep -q true && echo "-s -r --headless-rendering "',
                ' || echo "-r "',
            ]),
            'on_exit_shutdown': 'true',
        }.items(),
    )

    # 简化: 直接用 ExecuteProcess 启动 gz sim, 避免 Command 复杂拼接
    gz_args_str = '-r '
    # headless 模式加 -s
    gz_sim_exec = ExecuteProcess(
        cmd=['ign', 'gazebo', '-r', world_path],
        output='screen',
        condition=None,  # 默认 GUI 模式
    )

    # headless 版本
    gz_sim_headless = ExecuteProcess(
        cmd=['ign', 'gazebo', '-s', '-r', '--headless-rendering', world_path],
        output='screen',
    )

    # 用条件选择
    from launch.conditions import IfCondition, UnlessCondition
    gz_sim_gui = ExecuteProcess(
        cmd=['ign', 'gazebo', '-r', world_path],
        output='screen',
        condition=UnlessCondition(headless),
    )
    gz_sim_server = ExecuteProcess(
        cmd=['ign', 'gazebo', '-s', '-r', world_path],
        output='screen',
        condition=IfCondition(headless),
    )

    # ---- 2. Spawn 机器人 ----
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_rover',
        arguments=[
            '-name', robot_name,
            '-x', x,
            '-y', y,
            '-z', z,
            '-file', model_path,
        ],
        output='screen',
    )

    # ---- 3. ros_gz_bridge 桥接 ----
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        parameters=[{
            'config_file': bridge_path,
        }],
        output='screen',
        remappings=[
            # 保留默认话题名，与感知节点期望一致
        ],
    )

    # ---- 4. 图像桥接 (ros_gz_image 处理 Image 转换) ----
    image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        name='ros_gz_image_bridge',
        arguments=[
            '/world/road_inspection_world/model/rover/link/camera_frame/sensor/camera/image'
        ],
        output='screen',
    )

    # ---- 5. 静态 TF (map -> odom) ----
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_map_odom',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom'],
    )

    return LaunchDescription([
        # 参数
        headless_arg, world_arg, bridge_config_arg,
        robot_name_arg, x_arg, y_arg, z_arg,
        # 环境变量
        env_setup,
        # Gazebo (GUI 或 headless 二选一)
        gz_sim_gui,
        gz_sim_server,
        # Spawn 机器人
        spawn_robot,
        # 桥接
        bridge,
        # 图像桥接
        image_bridge,
        # 静态 TF
        static_tf,
    ])
