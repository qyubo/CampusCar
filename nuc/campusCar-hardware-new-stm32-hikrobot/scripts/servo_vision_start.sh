#!/usr/bin/env bash
# ============================================================
# 启动舵机视觉反馈控制节点
# ============================================================

set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${PROJECT_ROOT}/config/robot.env"

if [ -f "$ROS_SETUP" ]; then
    set +u
    # shellcheck disable=SC1090
    source "$ROS_SETUP"
    set -u
fi

# 查找STM32串口设备（UART1连接NUC）
STM32_DEVICE="${STM32_UART_DEVICE:-/dev/ttyUSB0}"

if [ ! -e "$STM32_DEVICE" ]; then
    echo "错误: STM32串口设备 $STM32_DEVICE 不存在"
    echo "请检查USB连接或修改 STM32_UART_DEVICE 环境变量"
    exit 1
fi

echo "启动舵机视觉控制节点..."
echo "  - STM32设备: $STM32_DEVICE"
echo "  - 图像话题: ${IMAGE_TOPIC:-/hikrobot_camera/image_raw}"

exec python3 "${PROJECT_ROOT}/src/servo_vision_controller.py" \
    --ros-args \
    -p stm32_device:="$STM32_DEVICE" \
    -p image_topic:="${IMAGE_TOPIC:-/hikrobot_camera/image_raw}" \
    -p image_compressed:=false \
    -p servo_control_mode:=target_tracking \
    -p target_y_ratio:=0.5 \
    -p kp:=0.3 \
    -p min_angle:=20 \
    -p max_angle:=160 \
    -p default_angle:=90
