#!/usr/bin/env bash
# 启动 CyberLuban 全链路节点（后台 setsid 脱离父进程），等就绪后采集 ROS2 接口
set -u
WS=/home/qyb413/CyberLuban/campus_road_inspection_ws
LOG=/tmp/cyber_logs
rm -rf "$LOG"; mkdir -p "$LOG"

# 公共环境
ENV_SETUP="source /opt/ros/humble/setup.bash; [ -f $WS/install/setup.bash ] && source $WS/install/setup.bash; export PYTHONPATH=$HOME/.local/lib/python3.10/site-packages:\$PYTHONPATH; export ROS_LOG_DIR=$LOG; export RCL_LOG_DIR=$LOG; export ROS_HOME=$LOG"

start() {
  local name="$1"; shift
  setsid bash -c "$ENV_SETUP; exec $*" >"$LOG/$name.log" 2>&1 < /dev/null &
  echo "  ▶ $name (pid $!)"
}

echo "=== 启动 8 个节点 ==="
start mock        "python3 $WS/test/mock_data_publisher.py"
sleep 3
start ground_seg  "ros2 run lidar_defect_detector ground_segmentation_node --ros-args -p num_sectors:=32 -p num_rings:=10 -p ground_threshold:=0.05 -p initial_seed_points:=50"
start lidar_det   "ros2 run lidar_defect_detector lidar_defect_detector_node --ros-args -p elevation_threshold_major:=0.008 -p min_cluster_size:=8"
start vision_det  "ros2 run vision_defect_detector vision_defect_detector_node --ros-args -p confidence_threshold:=0.4"
start fusion      "ros2 run sensor_fusion sensor_fusion_node --ros-args -p matching_distance_threshold:=1.0 -p time_sync_slop:=0.5"
start world       "ros2 run world_model world_model_node --ros-args -p prediction_horizon_days:=30 -p time_step_days:=10"
start roadmap     "ros2 run dynamic_roadmap dynamic_roadmap_node --ros-args -p grid_resolution:=0.5 -p enable_persistence:=false"
start ue5bridge   "ros2 run ue5_bridge ue5_bridge_node"

echo "=== 等待节点就绪 (15s) ==="
sleep 15

echo ""
echo "==================== ROS2 底层接口清单 ===================="
echo ""
echo "########## 1. ros2 node list ##########"
bash -c "$ENV_SETUP; ros2 node list"
echo ""
echo "########## 2. ros2 topic list ##########"
bash -c "$ENV_SETUP; ros2 topic list"
echo ""
echo "########## 3. ros2 service list ##########"
bash -c "$ENV_SETUP; ros2 service list"
echo ""
echo "########## 4. ros2 topic info (类型/订阅者/发布者) ##########"
for t in $(bash -c "$ENV_SETUP; ros2 topic list"); do
  echo "---- $t ----"
  bash -c "$ENV_SETUP; ros2 topic info -v $t" 2>/dev/null | head -15
done
echo ""
echo "########## 5. ros2 node info ##########"
for n in /mock_data_publisher /ground_segmentation_node /lidar_defect_detector_node /vision_defect_detector_node /sensor_fusion_node /world_model_node /dynamic_roadmap_node /ue5_bridge_node; do
  echo "---- $n ----"
  bash -c "$ENV_SETUP; ros2 node info $n" 2>/dev/null
done
echo ""
echo "########## 6. 关键话题 echo --once 采样 ##########"
echo "==== /livox/pointcloud (header) ===="
bash -c "$ENV_SETUP; timeout 8 ros2 topic echo --once /livox/pointcloud --field header"
echo "==== /camera/image_raw (header+size) ===="
bash -c "$ENV_SETUP; timeout 8 ros2 topic echo --once /camera/image_raw --field header; timeout 8 ros2 topic echo --once /camera/image_raw --field width; timeout 8 ros2 topic echo --once /camera/image_raw --field height"
echo "==== /camera/camera_info ===="
bash -c "$ENV_SETUP; timeout 8 ros2 topic echo --once /camera/camera_info" | head -30
echo "==== /odom ===="
bash -c "$ENV_SETUP; timeout 8 ros2 topic echo --once /odom" | head -30
echo "==== /perception/ground_cloud (header) ===="
bash -c "$ENV_SETUP; timeout 8 ros2 topic echo --once /perception/ground_cloud --field header"
echo "==== /perception/nonground_cloud (header) ===="
bash -c "$ENV_SETUP; timeout 8 ros2 topic echo --once /perception/nonground_cloud --field header"
echo "==== /perception/lidar_defects ===="
bash -c "$ENV_SETUP; timeout 12 ros2 topic echo --once /perception/lidar_defects"
echo "==== /perception/vision_defects ===="
bash -c "$ENV_SETUP; timeout 12 ros2 topic echo --once /perception/vision_defects"
echo "==== /perception/fused_defects ===="
bash -c "$ENV_SETUP; timeout 15 ros2 topic echo --once /perception/fused_defects"
echo "==== /prediction/defect_evolution ===="
bash -c "$ENV_SETUP; timeout 15 ros2 topic echo --once /prediction/defect_evolution"
echo "==== /roadmap/map_update ===="
bash -c "$ENV_SETUP; timeout 10 ros2 topic echo --once /roadmap/map_update"
echo "==== /ue5/robot_state ===="
bash -c "$ENV_SETUP; timeout 10 ros2 topic echo --once /ue5/robot_state"
echo ""
echo "########## 7. 服务调用 ##########"
echo "==== /roadmap/query_condition ===="
bash -c "$ENV_SETUP; timeout 12 ros2 service call /roadmap/query_condition cri_msgs/srv/QueryRoadCondition '{query_center: {x: 3.0, y: -2.0, z: 0.0}, query_radius: 3.0}'"
echo "==== /roadmap/request_detour ===="
bash -c "$ENV_SETUP; timeout 12 ros2 service call /roadmap/request_detour cri_msgs/srv/RequestDetourPath '{start_position: {x: -5.0, y: -5.0, z: 0.0}, goal_position: {x: 5.0, y: 5.0, z: 0.0}, avoid_defect_ids: []}'"
echo ""
echo "########## 8. 话题频率 ##########"
for t in /livox/pointcloud /camera/image_raw /odom /perception/ground_cloud /perception/fused_defects /prediction/defect_evolution /ue5/robot_state; do
  echo "---- hz: $t ----"
  bash -c "$ENV_SETUP; timeout 8 ros2 topic hz -w 15 $t" 2>/dev/null | tail -3
done
echo ""
echo "########## 9. 各节点日志 tail ##########"
for f in mock ground_seg lidar_det vision_det fusion world roadmap ue5bridge; do
  echo "---- $f.log (最后5行) ----"
  tail -5 "$LOG/$f.log" 2>/dev/null
done
echo ""
echo "==================== 接口采集完成 ===================="
echo "节点仍在后台运行, 你可新开终端继续观察:"
echo "  source /opt/ros/humble/setup.bash && source $WS/install/setup.bash"
echo "  ros2 topic echo /perception/fused_defects"
echo ""
echo "停止所有节点: pkill -9 -f '_node'; pkill -9 -f mock_data"
