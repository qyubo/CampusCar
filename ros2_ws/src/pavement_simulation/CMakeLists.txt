cmake_minimum_required(VERSION 3.8)
project(pavement_simulation)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ros_gz_sim REQUIRED)

# 安装 worlds / models / launch / config
install(DIRECTORY worlds models launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
