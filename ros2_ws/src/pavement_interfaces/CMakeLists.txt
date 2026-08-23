cmake_minimum_required(VERSION 3.8)
project(pavement_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/DefectInfo.msg"
  "msg/DefectArray.msg"
  "msg/DefectPrediction.msg"
  "msg/RoadCondition.msg"
  "msg/UE5Command.msg"
  "msg/UE5State.msg"
  "srv/QueryRoadCondition.srv"
  "srv/RequestDetourPath.srv"
  DEPENDENCIES std_msgs sensor_msgs geometry_msgs builtin_interfaces
)

ament_package()
