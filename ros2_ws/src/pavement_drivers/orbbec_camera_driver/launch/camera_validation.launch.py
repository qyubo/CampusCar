#!/usr/bin/env python3
"""只启动海康相机输入，便于先验证真实图像话题。"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    package_dir = get_package_share_directory('orbbec_camera_driver')
    config = os.path.join(package_dir, 'config', 'camera_params.yaml')
    return LaunchDescription([
        Node(
            package='orbbec_camera_driver',
            executable='hikrobot_camera_node',
            name='orbbec_camera',
            output='screen',
            parameters=[config],
        ),
    ])
