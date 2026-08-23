from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'lidar_obstacle_detector'

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
    description='LiDAR-based road defect detection with ground segmentation and DEM',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'lidar_defect_detector_node = lidar_obstacle_detector.lidar_defect_detector_node:main',
            'ground_segmentation_node = lidar_obstacle_detector.ground_segmentation_node:main',
        ],
    },
)
