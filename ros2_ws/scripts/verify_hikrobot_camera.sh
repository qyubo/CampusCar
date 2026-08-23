#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-humble}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/${ROS_DISTRO}/setup.bash}"
CAMERA_IP="${CAMERA_IP:-10.7.142.102}"
WIRED_IP="${WIRED_IP:-10.7.142.103}"
CAMERA_PACKAGE="${CAMERA_PACKAGE:-hikrobot_camera}"
IMAGE_TOPIC="${IMAGE_TOPIC:-/camera/image_raw}"
LOG_DIR="${LOG_DIR:-${WS_ROOT}/log/hikrobot_camera_validation}"

die() { echo "[ERROR] $*" >&2; exit 1; }
info() { echo "[INFO] $*"; }
ok() { echo "[ OK ] $*"; }

command -v ip >/dev/null 2>&1 || die "缺少 ip，请安装 iproute2"
command -v python3 >/dev/null 2>&1 || die "缺少 python3"

[[ -f "$ROS_SETUP" ]] || die "ROS 环境不存在: $ROS_SETUP。当前 Codex 容器没有 ROS，请在 NUC 上执行。"
# shellcheck disable=SC1090
source "$ROS_SETUP"
[[ -f "${WS_ROOT}/install/setup.bash" ]] || die "工作区尚未构建: ${WS_ROOT}/install/setup.bash"
# shellcheck disable=SC1091
source "${WS_ROOT}/install/setup.bash"

info "网卡地址与路由"
ip -br addr
ip route

WIRED_LINE="$(ip -o -4 addr show | awk -v ip="$WIRED_IP" '$4 ~ ("^" ip "/") {print}')"
[[ -n "$WIRED_LINE" ]] || die "未发现有线地址 ${WIRED_IP}；不能确认 enp1s0 配置。"
WIRED_IF="$(awk '{print $2}' <<< "$WIRED_LINE")"
[[ "$WIRED_IF" != "wlo1" ]] || die "${WIRED_IP} 配在 Wi-Fi wlo1，不是有线口。"
ok "${WIRED_IF}=${WIRED_IP}"

ROUTE_LINE="$(ip route get "$CAMERA_IP" 2>/dev/null || true)"
grep -q "dev ${WIRED_IF}" <<< "$ROUTE_LINE" || die "到 ${CAMERA_IP} 的路由不是 ${WIRED_IF}: ${ROUTE_LINE}"
ok "${CAMERA_IP} 通过 ${WIRED_IF}"

if command -v ethtool >/dev/null 2>&1; then
    ethtool "$WIRED_IF" | sed -n '1,80p'
fi
if [[ -r "/sys/class/net/${WIRED_IF}/carrier" ]]; then
    [[ "$(cat "/sys/class/net/${WIRED_IF}/carrier")" == "1" ]] || die "${WIRED_IF} 没有物理链路"
    ok "${WIRED_IF} carrier=1"
fi

ping -I "$WIRED_IF" -c 3 -W 2 "$CAMERA_IP" >/dev/null || die "${CAMERA_IP} 不可达；检查相机供电/IP/交换机/VLAN。"
ok "ping ${CAMERA_IP}"
if command -v arping >/dev/null 2>&1; then
    arping -I "$WIRED_IF" -c 3 -w 6 "$CAMERA_IP" || die "${CAMERA_IP} 没有 ARP 响应"
fi
ip neigh show dev "$WIRED_IF" || true

info "ROS/OpenCV/MVS 依赖"
command -v ros2 >/dev/null 2>&1 || die "ROS2 命令不可用"
python3 - <<'PY'
import importlib

for name in ('numpy', 'cv2', 'rclpy', 'cv_bridge'):
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        raise SystemExit(f'缺少 Python 依赖 {name}: {exc}')
    print(f'{name}: {getattr(module, "__file__", "ok")}')
PY

MVS_FOUND="$(find /opt/MVS /usr/local/MVS -type f -name 'MvCameraControl_class.py' 2>/dev/null | head -n 1 || true)"
[[ -n "$MVS_FOUND" ]] || die "未找到 MvCameraControl_class.py；请安装 Linux MVS SDK 后重试。"
ok "MVS Python wrapper: ${MVS_FOUND}"

info "重新构建相机包"
cd "$WS_ROOT"
command -v colcon >/dev/null 2>&1 || die "缺少 colcon"
colcon build --symlink-install --packages-select "$CAMERA_PACKAGE" cri_bringup
source "${WS_ROOT}/install/setup.bash"

mkdir -p "$LOG_DIR"
info "启动真实 MVS 相机，日志: ${LOG_DIR}/camera.log"
ros2 run "$CAMERA_PACKAGE" hikrobot_camera_node --ros-args \
    -p backend:=mvs \
    -p camera_ip:="$CAMERA_IP" \
    >"${LOG_DIR}/camera.log" 2>&1 &
CAMERA_PID=$!
cleanup() { kill "$CAMERA_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

sleep 2
if ! kill -0 "$CAMERA_PID" 2>/dev/null; then
    cat "${LOG_DIR}/camera.log"
    die "相机节点启动失败"
fi
grep -E '实际后端: mvs|MVS SDK 相机打开成功' "${LOG_DIR}/camera.log" || {
    cat "${LOG_DIR}/camera.log"
    die "相机节点未确认 MVS 后端"
}

info "等待 ${IMAGE_TOPIC} 首帧"
timeout 15 ros2 topic echo --once "$IMAGE_TOPIC" --field header
ros2 topic info "$IMAGE_TOPIC"
ros2 topic hz "$IMAGE_TOPIC" -w 5 || true
ok "真实图像已发布到 ${IMAGE_TOPIC}"
echo
echo "查看画面："
echo "  ros2 run rqt_image_view rqt_image_view"
echo "  选择 ${IMAGE_TOPIC}"
echo
echo "启动识别："
echo "  ros2 run vision_defect_detector vision_defect_detector_node"
