#!/usr/bin/env python3
"""
感知链路完整启动文件
启动顺序：地面分割 -> 激光检测 -> 视觉检测 -> 融合 -> 缺陷地理定位
"""
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # 配置文件路径
    lidar_config = os.path.join(
        get_package_share_directory('lidar_defect_detector'),
        'config', 'lidar_params.yaml'
    )
    
    vision_config = os.path.join(
        get_package_share_directory('vision_defect_detector'),
        'config', 'vision_params.yaml'
    )
    
    fusion_config = os.path.join(
        get_package_share_directory('sensor_fusion'),
        'config', 'fusion_params.yaml'
    )
    
    geolocation_config = os.path.join(
        get_package_share_directory('sensor_fusion'),
        'config', 'geolocation_params.yaml'
    )
    
    return LaunchDescription([
        # 1. 地面分割节点
        Node(
            package='lidar_defect_detector',
            executable='ground_segmentation_node',
            name='ground_segmentation',
            output='screen',
            parameters=[lidar_config]
        ),
        
        # 2. 激光缺陷检测节点
        Node(
            package='lidar_defect_detector',
            executable='lidar_defect_detector_node',
            name='lidar_defect_detector',
            output='screen',
            parameters=[lidar_config]
        ),
        
        # 3. 视觉缺陷检测节点
        Node(
            package='vision_defect_detector',
            executable='vision_defect_detector_node',
            name='vision_defect_detector',
            output='screen',
            parameters=[vision_config]
        ),
        
        # 4. 多传感器融合节点
        Node(
            package='sensor_fusion',
            executable='sensor_fusion_node',
            name='sensor_fusion',
            output='screen',
            parameters=[fusion_config]
        ),

        # 5. 缺陷地理定位节点
        Node(
            package='sensor_fusion',
            executable='defect_geolocation_node',
            name='defect_geo_localization_node',
            output='screen',
            parameters=[geolocation_config]
        ),
    ])
