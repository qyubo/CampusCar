#!/usr/bin/env bash
set -Eeuo pipefail

ROS_DISTRO="${ROS_DISTRO:-humble}"
MVS_URL="${MVS_URL:-https://www.hikrobotics.com/cn2/source/support/software/MVS_Linux_STD_V5.0.2_260728%EF%BC%881%EF%BC%89.zip}"
MVS_ARCHIVE="${MVS_ARCHIVE:-/tmp/MVS_Linux_STD_V5.0.2.zip}"

die() { echo "[ERROR] $*" >&2; exit 1; }
info() { echo "[INFO] $*"; }

[[ "${EUID}" -eq 0 ]] || die "请使用 sudo 运行: sudo $0"
command -v apt-get >/dev/null 2>&1 || die "当前系统没有 apt-get；请在 Ubuntu NUC 宿主机执行，而不是 Codex 容器。"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
    python3 \
    python3-numpy \
    python3-opencv \
    python3-pip \
    iproute2 \
    iputils-ping \
    ethtool \
    arping \
    unzip \
    ca-certificates \
    ros-${ROS_DISTRO}-cv-bridge \
    ros-${ROS_DISTRO}-image-transport \
    ros-${ROS_DISTRO}-rqt-image-view \
    ros-${ROS_DISTRO}-camera-aravis2 \
    aravis-tools \
    aravis-tools-cli

if [[ ! -f "$MVS_ARCHIVE" ]]; then
    command -v curl >/dev/null 2>&1 || apt-get install -y curl
    info "下载官方 Linux MVS SDK（约 816 MB）"
    curl --fail --location --retry 3 --output "$MVS_ARCHIVE" "$MVS_URL"
fi

[[ -s "$MVS_ARCHIVE" ]] || die "MVS 下载文件为空: $MVS_ARCHIVE"
MVS_INSTALL_ROOT="${MVS_INSTALL_ROOT:-/opt/MVS}"
mkdir -p "$MVS_INSTALL_ROOT"
unzip -q -o "$MVS_ARCHIVE" -d "$MVS_INSTALL_ROOT"

MVS_WRAPPER="$(find "$MVS_INSTALL_ROOT" -type f -name MvCameraControl_class.py -print -quit)"
MVS_LIBRARY="$(find "$MVS_INSTALL_ROOT" -type f -name 'libMvCameraControl.so*' -print -quit)"
[[ -n "$MVS_WRAPPER" ]] || die "MVS 压缩包中没有 MvCameraControl_class.py"
[[ -n "$MVS_LIBRARY" ]] || die "MVS 压缩包中没有 libMvCameraControl.so"

MVS_PYTHON_DIR="$(dirname "$MVS_WRAPPER")"
MVS_LIBRARY_DIR="$(dirname "$MVS_LIBRARY")"
cat >/etc/profile.d/hikrobot-mvs.sh <<EOF
export MVCAM_SDK_PATH="$MVS_PYTHON_DIR"
export MVS_SDK_PATH="$MVS_PYTHON_DIR"
export LD_LIBRARY_PATH="$MVS_LIBRARY_DIR:\${LD_LIBRARY_PATH:-}"
EOF

export MVCAM_SDK_PATH="$MVS_PYTHON_DIR"
export MVS_SDK_PATH="$MVS_PYTHON_DIR"
export LD_LIBRARY_PATH="$MVS_LIBRARY_DIR:${LD_LIBRARY_PATH:-}"
info "MVS Python wrapper: $MVS_WRAPPER"
info "MVS runtime library: $MVS_LIBRARY"
PYTHONPATH="$MVS_PYTHON_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 - <<'PY'
import importlib
module = importlib.import_module('MvCameraControl_class')
print('MVS Python import OK:', module.__file__)
PY

echo
echo "依赖安装完成。下一步："
echo "  source /opt/ros/${ROS_DISTRO}/setup.bash"
echo "  source /etc/profile.d/hikrobot-mvs.sh"
echo "  cd /home/qyb413/CyberLuban/campus_road_inspection_ws"
echo "  ./scripts/verify_hikrobot_camera.sh"
