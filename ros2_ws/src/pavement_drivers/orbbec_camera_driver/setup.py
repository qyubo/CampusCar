from setuptools import find_packages, setup

package_name = 'orbbec_camera_driver'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', ['config/camera_params.yaml', 'config/orbbec_params.yaml']),
        ('share/' + package_name + '/launch', ['launch/camera_validation.launch.py', 'launch/orbbec_camera.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='CRI Team',
    maintainer_email='dev@cri.robot',
    description='Hikrobot GigE and Orbbec RGBD camera drivers',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'hikrobot_camera_node = orbbec_camera_driver.hikrobot_camera_node:main',
            'hikrobot_real_camera_node = orbbec_camera_driver.hikrobot_real_camera_node:main',
            'orbbec_camera_node = orbbec_camera_driver.orbbec_camera_node:main',
        ],
    },
)
