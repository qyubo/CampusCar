#!/usr/bin/env python3
"""
算法层启动文件
启动顺序：世界模型 + 动态地图
"""
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # 配置文件路径
    world_model_config = os.path.join(
        get_package_share_directory('world_model'),
        'config', 'world_model_params.yaml'
    )
    
    roadmap_config = os.path.join(
        get_package_share_directory('digital_roadmap'),
        'config', 'roadmap_params.yaml'
    )
    
    return LaunchDescription([
        # 低秩动力学世界模型
        Node(
            package='world_model',
            executable='world_model_node',
            name='world_model',
            output='screen',
            parameters=[world_model_config]
        ),
        
        # 动态数字路面地图
        Node(
            package='digital_roadmap',
            executable='dynamic_roadmap_node',
            name='digital_roadmap',
            output='screen',
            parameters=[roadmap_config]
        ),
    ])
