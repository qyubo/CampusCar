#!/usr/bin/env bash
# ============================================================
# CyberLuban Gazebo + 感知联调一键启动脚本
# 启动: Gazebo仿真 + ros_gz桥接 + 8个感知节点
#
# 用法:
#   cd ~/CyberLuban/campus_road_inspection_ws
#   bash src/pavement_simulation/scripts/run_gazebo_perception.sh
# ============================================================
WS=/home/qyb413/CyberLuban/campus_road_inspection_ws
PKG_SHARE="$WS/install/pavement_simulation/share/pavement_simulation"
LOGDIR=/tmp/cyber_gp_logs
rm -rf "$LOGDIR"; mkdir -p "$LOGDIR"

# ---- 环境变量 ----
export ROS_HOME=/tmp/cyber_ros_home
export ROS_LOG_DIR=/tmp/cyber_ros_log
export RCL_LOG_DIR=/tmp/cyber_ros_log
export IGN_HOME=/tmp/ign_home
export IGN_GAZEBO_RESOURCE_PATH="$PKG_SHARE/models:${IGN_GAZEBO_RESOURCE_PATH:-}"
export GZ_SIM_RESOURCE_PATH="$IGN_GAZEBO_RESOURCE_PATH"
export PYTHONPATH="$HOME/.local/lib/python3.10/site-packages:$PYTHONPATH"
mkdir -p "$ROS_HOME" "$ROS_LOG_DIR" "$IGN_HOME"

source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash"

WORLD="$PKG_SHARE/worlds/road_inspection.sdf"
MODEL="$PKG_SHARE/models/rover/model.sdf"

pids=()
cleanup() {
  echo ""; echo "=== 清理所有进程 ==="
  for p in "${pids[@]}"; do kill -INT "$p" 2>/dev/null; done
  sleep 2
  for p in "${pids[@]}"; do kill -9 "$p" 2>/dev/null; done
  pkill -9 -f "ign gazebo" 2>/dev/null
  echo "=== 已清理 ==="
}
trap cleanup EXIT INT TERM

start_bg() {
  local name="$1"; shift
  echo "▶ $name"
  bash -c "source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; \
    export ROS_HOME=$ROS_HOME ROS_LOG_DIR=$ROS_LOG_DIR RCL_LOG_DIR=$RCL_LOG_DIR; \
    export PYTHONPATH=$PYTHONPATH; \
    exec \"\$@\"" bash "$@" >"$LOGDIR/${name}.log" 2>&1 &
  pids+=($!)
}

echo "============================================================"
echo "  CyberLuban Gazebo + 感知联调启动"
echo "============================================================"

# ---- 1. Gazebo (headless) ----
echo "▶ 启动 Gazebo (headless)"
ign gazebo -s -r --headless-rendering "$WORLD" > "$LOGDIR/gazebo.log" 2>&1 &
pids+=($!)
echo "  等待 Gazebo 启动 (8s)..."
sleep 8

# ---- 2. Spawn 机器人 ----
start_bg spawn ros2 run ros_gz_sim create -name rover -x 0.0 -y 0.0 -z 0.15 -file "$MODEL"
sleep 5

# ---- 3. ros_gz 桥接 (命令行格式, 解决 config_file 不转发大消息问题) ----
# 点云: /livox/scan/points (PointCloudPacked) -> /livox/pointcloud (PointCloud2)
start_bg bridge_pc ros2 run ros_gz_bridge parameter_bridge \
  /livox/scan/points@sensor_msgs/msg/PointCloud2@ignition.msgs.PointCloudPacked \
  --ros-args -p use_sim_time:=true -r /livox/scan/points:=/livox/pointcloud

# 图像: 用 ros_gz_image (parameter_bridge 对 Image 有转换问题)
start_bg bridge_img ros2 run ros_gz_image image_bridge /camera/image \
  --ros-args -p use_sim_time:=true -r /camera/image:=/camera/image_raw

# 其他话题: camera_info, odom, tf, imu, cmd_vel, clock
start_bg bridge_rest ros2 run ros_gz_bridge parameter_bridge \
  /camera/camera_info@sensor_msgs/msg/CameraInfo@ignition.msgs.CameraInfo \
  /odom@nav_msgs/msg/Odometry@ignition.msgs.Odometry \
  /tf@tf2_msgs/msg/TFMessage@ignition.msgs.Pose_V \
  /imu/data@sensor_msgs/msg/Imu@ignition.msgs.IMU \
  /cmd_vel@geometry_msgs/msg/Twist@ignition.msgs.Twist \
  /clock@rosgraph_msgs/msg/Clock@ignition.msgs.Clock \
  --ros-args -p use_sim_time:=true

# 静态 TF
start_bg static_tf ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 map odom \
  --ros-args -p use_sim_time:=true

echo "  等待桥接就绪 (8s)..."
sleep 8

# ---- 4. 感知节点 (use_sim_time) ----
start_bg ground_segmentation ros2 run lidar_obstacle_detector ground_segmentation_node \
  --ros-args -p use_sim_time:=true -p num_sectors:=32 -p num_rings:=10 \
  -p sensor_height:=0.35 -p ground_threshold:=0.05 -p initial_seed_points:=50
sleep 2

start_bg lidar_obstacle_detector ros2 run lidar_obstacle_detector lidar_defect_detector_node \
  --ros-args -p use_sim_time:=true -p elevation_threshold_major:=0.008 -p min_cluster_size:=8
sleep 2

start_bg vision_defect_detector ros2 run vision_defect_detector vision_defect_detector_node \
  --ros-args -p use_sim_time:=true -p confidence_threshold:=0.4
sleep 2

start_bg sensor_fusion ros2 run sensor_fusion sensor_fusion_node \
  --ros-args -p use_sim_time:=true -p matching_distance_threshold:=1.0 -p time_sync_slop:=0.5
sleep 1

# ---- 5. 算法层 ----
start_bg world_model ros2 run world_model world_model_node \
  --ros-args -p use_sim_time:=true -p prediction_horizon_days:=30 -p time_step_days:=10
sleep 1

start_bg digital_roadmap ros2 run digital_roadmap dynamic_roadmap_node \
  --ros-args -p use_sim_time:=true -p grid_resolution:=0.5 -p enable_persistence:=false
sleep 1

start_bg ue5_bridge ros2 run ue5_bridge ue5_bridge_node \
  --ros-args -p use_sim_time:=true

echo "  等待感知节点初始化 (15s)..."
sleep 15

# ---- 6. 移动机器人经过缺陷区域 ----
echo ""
echo "=== 移动机器人经过缺陷区域 ==="
echo "▶ 向 pothole(3,-2) 方向移动 10s"
timeout 10 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -0.15}}' \
  --rate 10 2>/dev/null | tail -1
sleep 2

echo "▶ 继续前进 8s"
timeout 8 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}' \
  --rate 10 2>/dev/null | tail -1
sleep 2

echo "▶ 停止"
timeout 2 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}' \
  --rate 10 2>/dev/null | tail -1
sleep 3

# ---- 7. 汇报结果 ----
echo ""
echo "============================================================"
echo "  联调结果"
echo "============================================================"

echo ""
echo "########## 节点列表 ##########"
ros2 node list 2>/dev/null

echo ""
echo "########## 话题频率 ##########"
for t in /livox/pointcloud /camera/image_raw /odom /imu/data /clock \
         /perception/ground_cloud /perception/lidar_defects \
         /perception/vision_defects /perception/fused_defects; do
  echo "--- hz: $t ---"
  timeout 6 ros2 topic hz "$t" 2>/dev/null | tail -1 | sed 's/^/    /'
done

echo ""
echo "########## 缺陷检测结果 ##########"
echo "--- /perception/lidar_defects ---"
timeout 8 ros2 topic echo --once /perception/lidar_defects 2>/dev/null | head -30 | sed 's/^/    /'
echo ""
echo "--- /perception/vision_defects ---"
timeout 8 ros2 topic echo --once /perception/vision_defects 2>/dev/null | head -30 | sed 's/^/    /'
echo ""
echo "--- /perception/fused_defects ---"
timeout 8 ros2 topic echo --once /perception/fused_defects 2>/dev/null | head -40 | sed 's/^/    /'

echo ""
echo "########## 里程计 (机器人最终位置) ##########"
timeout 5 ros2 topic echo --once /odom 2>/dev/null | grep -A4 "position" | head -5 | sed 's/^/    /'

echo ""
echo "########## 关键日志 ##########"
for f in ground_segmentation lidar_obstacle_detector vision_defect_detector sensor_fusion; do
  echo "--- $f.log (最后5行) ---"
  tail -5 "$LOGDIR/$f.log" 2>/dev/null | sed 's/^/    /'
done

echo ""
echo "============================================================"
echo "  联调完成! 仿真仍在后台运行 (Ctrl+C 退出)"
echo "  日志目录: $LOGDIR"
echo "============================================================"

while true; do sleep 1; done
