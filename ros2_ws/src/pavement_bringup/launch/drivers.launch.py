#!/usr/bin/env python3
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    """启动驱动层所有节点"""
    
    chassis_driver_dir = get_package_share_directory('chassis_driver')
    orbbec_camera_driver_dir = get_package_share_directory('orbbec_camera_driver')
    rtk_driver_dir = get_package_share_directory('rtk_gps_driver')
    
    return LaunchDescription([
        # 底盘驱动
        Node(
            package='chassis_driver',
            executable='chassis_driver_node',
            name='chassis_driver',
            output='screen',
            parameters=[os.path.join(chassis_driver_dir, 'config', 'chassis_params.yaml')]
        ),
        
        # Livox 雷达驱动
        Node(
            package='livox_lidar_driver',
            executable='livox_driver_node',
            name='livox_lidar_driver',
            output='screen',
        ),
        
        # 海康相机驱动
        Node(
            package='orbbec_camera_driver',
            executable='orbbec_camera_node',
            name='orbbec_camera_driver',
            output='screen',
            parameters=[os.path.join(orbbec_camera_driver_dir, 'config', 'camera_params.yaml')],
        ),

        # USB RTK GNSS / optional NTRIP correction driver
        Node(
            package='rtk_gps_driver',
            executable='rtk_gps_node',
            name='rtk_gps_node',
            output='screen',
            parameters=[os.path.join(rtk_driver_dir, 'config', 'rtk_params.yaml')],
        ),
    ])
