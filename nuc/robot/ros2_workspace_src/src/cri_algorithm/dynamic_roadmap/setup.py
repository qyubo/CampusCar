from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'dynamic_roadmap'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='CRI Team',
    maintainer_email='dev@cri.robot',
    description='Dynamic digital road map with multi-layer grid and incremental updates',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'dynamic_roadmap_node = dynamic_roadmap.dynamic_roadmap_node:main',
            'fixed_waypoint_follower_node = dynamic_roadmap.fixed_waypoint_follower_node:main',
        ],
    },
)
