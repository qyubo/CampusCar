from setuptools import find_packages, setup


package_name = "rtk_gps_driver"

setup(
    name=package_name,
    version="1.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", ["config/rtk_params.yaml"]),
        (
            "share/" + package_name + "/launch",
            ["launch/rtk_gps.launch.py"],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="CRI Team",
    maintainer_email="dev@cri.robot",
    description="ROS2 Python driver for NMEA GNSS and optional NTRIP RTCM corrections",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "rtk_gps_node = rtk_gps_driver.rtk_gps_node:main",
            "rtk_serial_monitor = rtk_gps_driver.serial_monitor:main",
        ],
    },
)
