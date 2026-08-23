#!/usr/bin/env python3
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    """启动完整系统的所有节点"""
    
    cri_bringup_dir = get_package_share_directory('cri_bringup')
    
    return LaunchDescription([
        # 驱动层
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(cri_bringup_dir, 'launch', 'drivers.launch.py')
            )
        ),
        
        # UE5 桥接
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(get_package_share_directory('ue5_bridge'), 'launch', 'ue5_bridge.launch.py')
            )
        ),
        
        # 感知层：地面分割、激光检测、视觉检测、融合、地理定位
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(cri_bringup_dir, 'launch', 'perception.launch.py')
            )
        ),
        
        # TODO: 导航层启动项
    ])
