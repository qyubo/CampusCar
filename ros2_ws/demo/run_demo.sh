#!/bin/bash
echo "========================================"
echo "路面缺陷检测Demo - 快速启动"
echo "========================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] 未找到Python，请先安装Python 3.8+"
    exit 1
fi

echo "[1/3] 检查依赖..."
python3 -c "import ultralytics" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[INFO] 未安装ultralytics，正在安装..."
    pip3 install ultralytics opencv-python numpy
    if [ $? -ne 0 ]; then
        echo "[ERROR] 安装失败"
        exit 1
    fi
else
    echo "[OK] 依赖已安装"
fi

echo "[2/3] 启动检测..."
python3 demo_road_defect_detection.py --source demo

echo ""
echo "[3/3] 完成！"
echo "结果保存在: demo/output/"
echo ""
