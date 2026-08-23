#!/usr/bin/env bash
# ============================================================
# CyberLuban Gazebo 仿真一键启动脚本
# 解决 ~/.ros/log 只读沙箱限制 + 启动完整仿真链路
#
# 用法:
#   cd ~/CyberLuban/campus_road_inspection_ws
#   bash src/pavement_simulation/scripts/run_gazebo.sh              # GUI 模式
#   bash src/pavement_simulation/scripts/run_gazebo.sh --headless   # 无头模式
# ============================================================
WS=/home/qyb413/CyberLuban/campus_road_inspection_ws
PKG_SHARE="$WS/install/pavement_simulation/share/pavement_simulation"

# ---- 解决 ~/.ros/log 只读问题: 重定向到 /tmp ----
export ROS_HOME=/tmp/cyber_ros_home
export ROS_LOG_DIR=/tmp/cyber_ros_log
export RCL_LOG_DIR=/tmp/cyber_ros_log
mkdir -p "$ROS_HOME" "$ROS_LOG_DIR"

# ---- Gazebo 模型路径 ----
export IGN_GAZEBO_RESOURCE_PATH="$PKG_SHARE/models:${IGN_GAZEBO_RESOURCE_PATH:-}"
export GZ_SIM_RESOURCE_PATH="$PKG_SHARE/models:${GZ_SIM_RESOURCE_PATH:-}"

# ---- Python 依赖路径 ----
export PYTHONPATH="$HOME/.local/lib/python3.10/site-packages:$PYTHONPATH"

# ---- Source ROS2 + 工作空间 ----
source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash"

MODE="gui"
if [ "${1:-}" = "--headless" ] || [ "${2:-}" = "--headless" ]; then
  MODE="headless"
fi

WORLD="$PKG_SHARE/worlds/road_inspection.sdf"
MODEL="$PKG_SHARE/models/rover/model.sdf"
BRIDGE_CFG="$PKG_SHARE/config/bridge.yaml"

LOGDIR=/tmp/cyber_gazebo_logs
rm -rf "$LOGDIR"; mkdir -p "$LOGDIR"

echo "============================================================"
echo "  CyberLuban Gazebo 仿真启动 ($MODE 模式)"
echo "============================================================"
echo "  World:  $WORLD"
echo "  Model:  $MODEL"
echo "  Bridge: $BRIDGE_CFG"
echo "  Logs:   $LOGDIR"
echo "============================================================"
echo ""

pids=()
cleanup() {
  echo ""
  echo "=== 清理所有进程 ==="
  for p in "${pids[@]}"; do
    kill -INT "$p" 2>/dev/null
  done
  sleep 2
  for p in "${pids[@]}"; do
    kill -9 "$p" 2>/dev/null
  done
  echo "=== 已清理 ==="
}
trap cleanup EXIT INT TERM

# ---- 1. 启动 Gazebo ----
if [ "$MODE" = "headless" ]; then
  echo "▶ 启动 Gazebo (headless server)"
  ign gazebo -s -r --headless-rendering "$WORLD" > "$LOGDIR/gazebo.log" 2>&1 &
else
  echo "▶ 启动 Gazebo (GUI)"
  ign gazebo -r "$WORLD" > "$LOGDIR/gazebo.log" 2>&1 &
fi
pids+=($!)

echo "  等待 Gazebo 启动 (8s)..."
sleep 8

# ---- 2. Spawn 机器人 ----
echo "▶ Spawn 机器人 rover"
ros2 run ros_gz_sim create -name rover -x 0.0 -y 0.0 -z 0.15 \
  -file "$MODEL" > "$LOGDIR/spawn.log" 2>&1 &
pids+=($!)

sleep 5

# ---- 3. 启动 ros_gz_bridge ----
echo "▶ 启动 ros_gz_bridge (话题桥接)"
ros2 run ros_gz_bridge parameter_bridge --ros-args \
  -p config_file:="$BRIDGE_CFG" > "$LOGDIR/bridge.log" 2>&1 &
pids+=($!)

# ---- 4. 启动 image_bridge ----
echo "▶ 启动 ros_gz_image_bridge (图像桥接)"
ros2 run ros_gz_image image_bridge \
  /world/road_inspection_world/model/rover/link/camera_frame/sensor/camera/image \
  > "$LOGDIR/image_bridge.log" 2>&1 &
pids+=($!)

# ---- 5. 静态 TF ----
echo "▶ 启动静态 TF (map -> odom)"
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 map odom \
  > "$LOGDIR/static_tf.log" 2>&1 &
pids+=($!)

echo ""
echo "=== 等待桥接就绪 (10s) ==="
sleep 10

echo ""
echo "============================================================"
echo "  Gazebo 仿真运行中! ROS2 接口清单:"
echo "============================================================"

echo ""
echo "########## ros2 node list ##########"
ros2 node list 2>/dev/null

echo ""
echo "########## ros2 topic list ##########"
ros2 topic list 2>/dev/null

echo ""
echo "########## ros2 topic info (类型) ##########"
for t in /livox/pointcloud /camera/image_raw /camera/camera_info /odom /imu/data /cmd_vel /clock /tf; do
  echo "--- $t ---"
  ros2 topic info "$t" 2>/dev/null | sed 's/^/    /'
done

echo ""
echo "########## 话题数据采样 ##########"
echo "==== /livox/pointcloud (header) ===="
timeout 8 ros2 topic echo --once /livox/pointcloud --field header 2>/dev/null | head -5

echo "==== /camera/image_raw (header+尺寸) ===="
timeout 8 ros2 topic echo --once /camera/image_raw --field header 2>/dev/null | head -5
timeout 8 ros2 topic echo --once /camera/image_raw --field width 2>/dev/null | head -2
timeout 8 ros2 topic echo --once /camera/image_raw --field height 2>/dev/null | head -2

echo "==== /camera/camera_info ===="
timeout 8 ros2 topic echo --once /camera/camera_info 2>/dev/null | head -20

echo "==== /odom ===="
timeout 8 ros2 topic echo --once /odom 2>/dev/null | head -25

echo "==== /imu/data ===="
timeout 8 ros2 topic echo --once /imu/data 2>/dev/null | head -20

echo "==== /clock ===="
timeout 5 ros2 topic echo --once /clock 2>/dev/null | head -5

echo ""
echo "########## 话题频率 ##########"
for t in /livox/pointcloud /camera/image_raw /odom /imu/data /clock; do
  echo "--- hz: $t ---"
  timeout 8 ros2 topic hz -w 10 "$t" 2>/dev/null | tail -3 | sed 's/^/    /'
done

echo ""
echo "########## 发送速度指令测试 ##########"
echo "▶ 发送 cmd_vel (0.3 m/s, 0.2 rad/s) 持续 3s"
timeout 3 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.2}}' \
  --rate 10 2>/dev/null | tail -3
sleep 1
echo "▶ 采样移动后的 /odom:"
timeout 5 ros2 topic echo --once /odom 2>/dev/null | grep -A3 "position" | head -5

echo ""
echo "########## 各进程日志 tail ##########"
for f in gazebo spawn bridge image_bridge static_tf; do
  echo "--- $f.log (最后3行) ---"
  tail -3 "$LOGDIR/$f.log" 2>/dev/null
done

echo ""
echo "============================================================"
echo "  Gazebo 仿真验证完成!"
echo "  仿真仍在后台运行, 你可新开终端继续观察:"
echo "    source /opt/ros/humble/setup.bash"
echo "    source $WS/install/setup.bash"
echo "    export ROS_HOME=/tmp/cyber_ros_home"
echo "    ros2 topic echo /livox/pointcloud"
echo "    ros2 topic echo /camera/image_raw"
echo "    ros2 topic pub /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.2}, angular: {z: 0.1}}'"
echo ""
echo "  按 Ctrl+C 停止仿真"
echo "============================================================"

# 挂起, 等待用户 Ctrl+C
while true; do sleep 1; done
