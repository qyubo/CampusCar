#!/usr/bin/env python3
"""
算法层启动文件
启动顺序：世界模型 + 动态地图 + 固定经纬度线路跟随
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
        get_package_share_directory('dynamic_roadmap'),
        'config', 'roadmap_params.yaml'
    )

    waypoint_config = os.path.join(
        get_package_share_directory('dynamic_roadmap'),
        'config', 'fixed_waypoint_follower_params.yaml'
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
            package='dynamic_roadmap',
            executable='dynamic_roadmap_node',
            name='dynamic_roadmap',
            output='screen',
            parameters=[roadmap_config]
        ),

        # 固定经纬度线路跟随
        Node(
            package='dynamic_roadmap',
            executable='fixed_waypoint_follower_node',
            name='fixed_waypoint_follower_node',
            output='screen',
            parameters=[waypoint_config]
        ),
    ])
