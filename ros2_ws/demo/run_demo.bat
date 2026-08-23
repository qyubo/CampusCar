@echo off
echo ========================================
echo 路面缺陷检测Demo - 快速启动
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
python -c "import ultralytics" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 未安装ultralytics，正在安装...
    pip install ultralytics opencv-python numpy
    if errorlevel 1 (
        echo [ERROR] 安装失败
        pause
        exit /b 1
    )
) else (
    echo [OK] 依赖已安装
)

echo [2/3] 启动检测...
python demo_road_defect_detection.py --source demo

echo.
echo [3/3] 完成！
echo 结果保存在: demo\output\
echo.
pause
