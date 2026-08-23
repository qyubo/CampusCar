from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'world_model'

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
    description='Low-rank dynamical world model with SVD and Paris law',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'world_model_node = world_model.world_model_node:main',
        ],
    },
)
