#!/usr/bin/env python3
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ue5_bridge',
            executable='ue5_bridge_node',
            name='ue5_bridge',
            output='screen',
            parameters=[{
                'bridge_mode': 'bidirectional',
            }]
        ),
    ])
