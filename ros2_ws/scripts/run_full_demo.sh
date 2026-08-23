#!/usr/bin/env bash
# ==============================================================
# CyberLuban Campus Road Inspection —— 一键启动 + 接口验证脚本
# 功能:
#   1. 启动 mock 数据发布器 (替代真实硬件)
#   2. 启动完整感知链路 (地面分割 + 激光检测 + 视觉检测 + 融合)
#   3. 启动完整算法链路 (世界模型 + 动态地图)
#   4. 启动 UE5 虚实桥接
#   5. 运行 demo/quick_demo.py 做端到端功能演示
#   6. 轮询所有话题/节点/服务/消息类型与 echo 样本
# 用法:
#   cd campus_road_inspection_ws && bash scripts/run_full_demo.sh
# ==============================================================
set -u

WS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$WS_DIR/demo/log"
mkdir -p "$LOG_DIR"

# 确保 .local 的 numpy/cv2 优先于 ros 自带老版本
export PYTHONPATH="$HOME/.local/lib/python3.10/site-packages:$PYTHONPATH"
export ROS_LOG_DIR="$LOG_DIR/ros"
export RCL_LOG_DIR="$ROS_LOG_DIR"
export ROS_HOME="$LOG_DIR/ros_home"
mkdir -p "$ROS_LOG_DIR" "$ROS_HOME"

source /opt/ros/humble/setup.bash
if [ -f "$WS_DIR/install/setup.bash" ]; then
    source "$WS_DIR/install/setup.bash"
fi

echo "=== CyberLuban 完整 Demo 启动 ==="
echo "WS_DIR=$WS_DIR"
echo "LOG_DIR=$LOG_DIR"
echo ""

pids=()
kill_all() {
  echo ""
  echo "=== 接收到退出信号, 关闭所有子进程 (${#pids[@]}) ==="
  for pid in "${pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill -INT "$pid" 2>/dev/null
    fi
  done
  sleep 2
  for pid in "${pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null
    fi
  done
  echo "✅ 已关闭"
}
trap kill_all EXIT INT TERM

start_node() {
  local name="$1"; shift
  local log="$LOG_DIR/${name}.log"
  echo "▶ 启动: $name -> $log"
  ( bash -c "source /opt/ros/humble/setup.bash; \
     [ -f $WS_DIR/install/setup.bash ] && source $WS_DIR/install/setup.bash; \
     export PYTHONPATH=$HOME/.local/lib/python3.10/site-packages:\$PYTHONPATH; \
     export ROS_LOG_DIR=$ROS_LOG_DIR; \
     export RCL_LOG_DIR=$RCL_LOG_DIR; \
     export ROS_HOME=$ROS_HOME; \
     exec \"\$@\"" bash "$@" ) >"$log" 2>&1 &
  pids+=($!)
}

# 1) mock 数据 (硬件替代)
start_node mock_data_publisher \
  python3 "$WS_DIR/test/mock_data_publisher.py"

sleep 5

# 2) 感知层 4 个节点
start_node ground_segmentation \
  ros2 run lidar_defect_detector ground_segmentation_node --ros-args \
    -p num_sectors:=32 -p num_rings:=10 -p ground_threshold:=0.05 -p initial_seed_points:=50

sleep 1

start_node lidar_defect_detector \
  ros2 run lidar_defect_detector lidar_defect_detector_node --ros-args \
    -p elevation_threshold_major:=0.008 -p min_cluster_size:=8

sleep 1

start_node vision_defect_detector \
  ros2 run vision_defect_detector vision_defect_detector_node --ros-args \
    -p confidence_threshold:=0.4

sleep 1

start_node sensor_fusion \
  ros2 run sensor_fusion sensor_fusion_node --ros-args \
    -p matching_distance_threshold:=1.0 -p time_sync_slop:=0.5

sleep 1

# 3) 算法层 2 个节点
start_node world_model \
  ros2 run world_model world_model_node --ros-args \
    -p prediction_horizon_days:=30 -p time_step_days:=10

sleep 1

start_node dynamic_roadmap \
  ros2 run dynamic_roadmap dynamic_roadmap_node --ros-args \
    -p grid_resolution:=0.5 -p enable_persistence:=false

sleep 1

# 4) UE5 桥接
start_node ue5_bridge \
  ros2 run ue5_bridge ue5_bridge_node

sleep 1

echo ""
echo "=== 等待系统进入稳态 (10s) ==="
sleep 10

echo ""
echo "=== 正在运行的节点 ==="
ros2 node list 2>/dev/null
echo ""
echo "=== 正在运行的话题 ==="
ros2 topic list 2>/dev/null
echo ""
echo "=== 正在运行的服务 ==="
ros2 service list 2>/dev/null
echo ""
echo "=== 每个话题的消息类型 (ros2 topic info) ==="
for t in $(ros2 topic list 2>/dev/null | grep -vE "^$"); do
  echo "--- $t ---"
  ros2 topic info "$t" 2>/dev/null | sed 's/^/    /'
done

echo ""
echo "=== 关键节点详情 ==="
for n in /mock_data_publisher /ground_segmentation_node /lidar_defect_detector_node \
         /vision_defect_detector_node /sensor_fusion_node /world_model_node \
         /dynamic_roadmap_node /ue5_bridge_node; do
  echo "--- $n ---"
  ros2 node info "$n" 2>/dev/null | sed 's/^/    /'
done

echo ""
echo "=== 关键话题采样 (ros2 topic echo --once) ==="
sample_topic() {
  local t="$1"
  local limit="${2:-40}"
  echo "--- $t ---"
  timeout 12 ros2 topic echo --once "$t" 2>/dev/null | head -n "$limit" | sed 's/^/    /'
  echo ""
}
sample_topic /livox/pointcloud 20
sample_topic /camera/camera_info 25
sample_topic /odom 30
sample_topic /perception/ground_cloud 15
sample_topic /perception/nonground_cloud 15
sample_topic /perception/lidar_defects 60
sample_topic /perception/vision_defects 60
sample_topic /perception/fused_defects 80
sample_topic /prediction/defect_evolution 60
sample_topic /roadmap/map_update 30
sample_topic /ue5/robot_state 60

echo ""
echo "=== 调用服务 /roadmap/query_condition ==="
timeout 15 ros2 service call /roadmap/query_condition cri_msgs/srv/QueryRoadCondition \
  "{query_center: {x: 3.0, y: -2.0, z: 0.0}, query_radius: 3.0}" 2>/dev/null | sed 's/^/    /'
echo ""
echo "=== 调用服务 /roadmap/request_detour ==="
timeout 15 ros2 service call /roadmap/request_detour cri_msgs/srv/RequestDetourPath \
  "{start_position: {x: -5.0, y: -5.0, z: 0.0}, goal_position: {x: 5.0, y: 5.0, z: 0.0}, avoid_defect_ids: []}" 2>/dev/null | sed 's/^/    /'

echo ""
echo "=== 运行 ROS2 外 demo: demo/quick_demo.py ==="
(
  source /opt/ros/humble/setup.bash
  [ -f "$WS_DIR/install/setup.bash" ] && source "$WS_DIR/install/setup.bash"
  export PYTHONPATH="$HOME/.local/lib/python3.10/site-packages:$PYTHONPATH"
  timeout 60 python3 "$WS_DIR/demo/quick_demo.py" 2>&1 | sed 's/^/    /' | tail -60
) || true

echo ""
echo "=== 话题发布频率 (ros2 topic hz -w 30 采样) ==="
for t in /livox/pointcloud /camera/image_raw /odom /perception/fused_defects /prediction/defect_evolution; do
  echo "--- hz: $t ---"
  timeout 8 ros2 topic hz -w 30 "$t" 2>/dev/null | tail -5 | sed 's/^/    /'
  echo ""
done

echo ""
echo "=== Demo 完成, 继续挂起 (Ctrl+C 结束) ==="
echo "日志目录: $LOG_DIR"
echo "你可新开终端: source /opt/ros/humble/setup.bash && source $WS_DIR/install/setup.bash"
echo "然后 ros2 topic list / ros2 node list / ros2 topic echo ... 继续查看底层接口"

while true; do sleep 1; done
