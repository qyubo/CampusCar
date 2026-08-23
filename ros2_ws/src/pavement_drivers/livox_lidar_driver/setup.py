from setuptools import find_packages, setup

package_name = 'livox_lidar_driver'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', ['config/livox_params.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='CRI Team',
    maintainer_email='dev@cri.robot',
    description='Livox Mid-360S LiDAR driver',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'livox_driver_node = livox_lidar_driver.livox_driver_node:main',
        ],
    },
)
