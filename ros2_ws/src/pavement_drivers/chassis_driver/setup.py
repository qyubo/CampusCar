from setuptools import find_packages, setup

package_name = 'chassis_driver'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', ['config/chassis_params.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='CRI Team',
    maintainer_email='dev@cri.robot',
    description='Chassis driver for differential drive robot with STM32 controller',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'chassis_driver_node = chassis_driver.chassis_driver_node:main',
        ],
    },
)
