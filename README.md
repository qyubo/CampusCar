# CampusCar 智能校园巡检机器人

基于ROS2的智能校园巡检机器人系统，集成视觉缺陷检测、RTK GPS定位、动态路径规划等功能，用于校园道路病害自动巡检。

## 项目简介

CampusCar是一个完整的校园巡检机器人解决方案，包含底盘控制、感知系统、决策算法和上位机软件。系统采用模块化设计，支持：

- **自主巡检**：基于GPS航点的自动巡航
- **缺陷检测**：实时视觉检测路面裂缝、坑洼等病害
- **精确定位**：RTK GPS厘米级定位
- **远程控制**：支持UE5虚拟环境远程操控
- **数据管理**：缺陷地理位置标注与数据导出

## 运行环境

### 硬件平台
- **底盘控制器**：STM32H723VGT6
- **上位机**：Intel NUC（或同等x86-64主机）
- **电调**：Hoverboard电调
- **传感器**：
  - Orbbec深度相机
  - RTK GPS模块
  - 舵机（MG996R或同等型号）

### 软件环境
- **操作系统**：Ubuntu 22.04 LTS
- **ROS版本**：ROS2 Humble
- **开发工具**：
  - STM32CubeIDE / ARM工具链
  - Python 3.10+
  - OpenCV 4.x
  - 虚幻引擎5（可选，用于远程控制）

## 项目结构

```
CampusCar/
├── CampusCar_STM32H723VGT6/      # STM32底盘控制固件
│   ├── Core/                      # 核心代码（串口、舵机、电调控制）
│   ├── docs/                      # 固件文档
│   └── README.md                  # 固件说明
│
├── nuc/                           # NUC上位机代码
│   └── robot/
│       └── ros2_workspace_src/    # ROS2工作空间
│           ├── src/
│           │   ├── cri_drivers/   # 硬件驱动（底盘、相机、GPS）
│           │   ├── cri_perception/ # 感知模块（视觉检测、传感器融合）
│           │   ├── cri_algorithm/  # 算法模块（路径规划、导航）
│           │   └── cri_bringup/   # 启动配置
│           └── scripts/           # 工具脚本
│
├── docs/                          # 项目文档
│   ├── CampusCar开发文档_链路舵机协议回滚_v20260820.md
│   ├── PROJECT_SUMMARY.md         # 项目总结
│   ├── STM32H723_USART控制源码使用教程.md
│   ├── 串口协议说明.md
│   ├── PWM切换组合参数使用说明.md
│   ├── servo_control_guide.md     # 舵机控制指南
│   ├── orbbec_defect_operation.md # Orbbec缺陷检测操作指南
│   └── ...                        # 其他技术文档
│
├── calibration_images/            # 相机标定图像
├── camera_calibration.py          # 相机标定工具
├── CAMERA_CALIBRATION_README.md   # 相机标定说明
└── README.md                      # 本文件
```

## 安装方式

### 1. 克隆仓库

```bash
git clone <your-repo-url>
cd CampusCar
```

### 2. STM32固件编译与烧录

详见 [CampusCar_STM32H723VGT6/README.md](CampusCar_STM32H723VGT6/README.md)

```bash
cd CampusCar_STM32H723VGT6
# 使用STM32CubeIDE打开项目编译，或使用CMake
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../cmake/gcc-arm-none-eabi.cmake ..
make
# 烧录固件
openocd -f interface/stlink.cfg -f target/stm32h7x.cfg \
  -c "program CampusCar_STM32H723VGT6.elf verify reset exit"
```

### 3. ROS2工作空间配置

#### 安装依赖

```bash
# ROS2 Humble安装（如未安装）
sudo apt update
sudo apt install ros-humble-desktop

# 安装项目依赖
sudo apt install \
  python3-pip \
  python3-opencv \
  ros-humble-cv-bridge \
  ros-humble-image-transport \
  ros-humble-nav2-* \
  ros-humble-geographic-msgs
```

#### 编译工作空间

```bash
cd nuc/robot/ros2_workspace_src
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### 4. 相机标定（首次使用）

详见 [CAMERA_CALIBRATION_README.md](CAMERA_CALIBRATION_README.md)

```bash
# 采集标定图像
./calibrate_camera.sh

# 执行标定
python3 camera_calibration.py
```

## 使用说明

### 快速启动

#### 1. 启动完整系统

```bash
cd nuc/robot/ros2_workspace_src
source install/setup.bash

# 启动所有节点（底盘驱动、相机、GPS、算法）
ros2 launch cri_bringup full_system.launch.py
```

#### 2. 启动各子系统

**底盘驱动**：
```bash
ros2 launch cri_bringup chassis.launch.py
```

**感知系统**（相机+视觉检测）：
```bash
ros2 launch cri_bringup perception.launch.py
```

**导航算法**：
```bash
ros2 launch cri_bringup algorithm.launch.py
```

### 典型使用场景

#### 场景1：自主巡检

1. 启动完整系统
2. 发送GPS航点：
   ```bash
   ros2 topic pub /waypoints geographic_msgs/msg/GeoPoseStamped "..."
   ```
3. 机器人自动巡航并检测路面缺陷
4. 查看检测结果：
   ```bash
   ros2 topic echo /defect_locations
   ```

#### 场景2：远程手动控制

1. 启动底盘驱动
2. 通过UE5或键盘控制：
   ```bash
   # 键盘控制
   ros2 run teleop_twist_keyboard teleop_twist_keyboard
   
   # 或使用舵机键盘控制
   python3 scripts/servo_keyboard_control.py
   ```

#### 场景3：缺陷标注与数据采集

详见 [docs/orbbec_defect_operation.md](docs/orbbec_defect_operation.md)

1. 启动缺陷检测：
   ```bash
   ./scripts/orbbec_defect_control.sh start
   ```
2. 机器人行驶过程中自动检测并标注
3. 导出数据：
   ```bash
   ros2 service call /export_defects std_srvs/srv/Trigger
   ```

### 配置说明

#### 串口配置

编辑 `nuc/robot/ros2_workspace_src/src/cri_drivers/chassis_driver/config/chassis_params.yaml`：

```yaml
serial_port: "/dev/ttyUSB0"  # 串口设备
baud_rate: 115200             # 波特率
```

#### 相机配置

编辑 `nuc/robot/ros2_workspace_src/src/cri_drivers/hikrobot_camera/config/orbbec_params.yaml`：

```yaml
device_num: 0                # 相机编号
frame_rate: 30               # 帧率
resolution: [640, 480]       # 分辨率
```

#### GPS配置

编辑 `nuc/robot/ros2_workspace_src/src/cri_drivers/rtk_gps_driver/config/rtk_params.yaml`：

```yaml
serial_port: "/dev/ttyUSB1"
baud_rate: 115200
```

## 技术文档

### STM32固件相关
- [STM32固件README](CampusCar_STM32H723VGT6/README.md)
- [STM32H723 USART控制源码使用教程](docs/STM32H723_USART控制源码使用教程.md)
- [串口协议说明](docs/串口协议说明.md)
- [PWM切换组合参数使用说明](docs/PWM切换组合参数使用说明.md)
- [舵机控制指南](docs/servo_control_guide.md)

### ROS2系统相关
- [项目总结](docs/PROJECT_SUMMARY.md)
- [开发文档](docs/CampusCar开发文档_链路舵机协议回滚_v20260820.md)
- [Orbbec缺陷检测操作指南](docs/orbbec_defect_operation.md)

### 相机标定
- [相机标定README](CAMERA_CALIBRATION_README.md)
- [标定板规格说明](CHESSBOARD_SPEC.md)

## 常见问题

### 1. 串口无法打开

**问题**：`Permission denied: '/dev/ttyUSB0'`

**解决**：
```bash
sudo chmod 666 /dev/ttyUSB0
# 或永久添加用户到dialout组
sudo usermod -aG dialout $USER
# 重新登录生效
```

### 2. 相机无法识别

**问题**：找不到相机设备

**解决**：
```bash
# 检查USB设备
lsusb | grep Orbbec

# 检查相机权限
sudo chmod 666 /dev/video*

# 重启相机节点
ros2 run hikrobot_camera orbbec_camera_node
```

### 3. ROS2节点无法通信

**问题**：节点之间无法接收消息

**解决**：
```bash
# 检查ROS_DOMAIN_ID
echo $ROS_DOMAIN_ID

# 检查网络配置
ros2 doctor --report

# 重新source环境
source /opt/ros/humble/setup.bash
source install/setup.bash
```

### 4. STM32舵机不动

**问题**：舵机无响应

**解决**：见 [STM32固件README - 常见问题](CampusCar_STM32H723VGT6/README.md#常见问题)

## 开发指南

### 添加新的ROS2节点

1. 在相应package中创建节点：
   ```bash
   cd nuc/robot/ros2_workspace_src/src/cri_<module>/
   touch <module>/<your_node>.py
   chmod +x <module>/<your_node>.py
   ```

2. 在 `setup.py` 中注册：
   ```python
   entry_points={
       'console_scripts': [
           'your_node = module.your_node:main',
       ],
   }
   ```

3. 重新编译：
   ```bash
   colcon build --packages-select cri_<module>
   ```

### 修改STM32固件

1. 打开CubeMX配置文件修改外设
2. 用户代码写在 `USER CODE BEGIN/END` 块内
3. 重新编译并烧录

### 贡献代码

1. Fork本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "Add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 提交Pull Request

## 版本历史

### v2.0.0 (2026-08-23)
- 🔧 修复STM32舵机GPIO配置问题
- 📝 完善项目文档结构
- 🗂️ 整理文档到docs目录
- ✨ 添加完整的README说明

### v1.0.0 (2026-08-21)
- ✨ 初始版本发布
- ✅ 完成STM32底盘控制
- ✅ 集成ROS2驱动和算法
- ✅ 实现视觉缺陷检测
- ✅ 支持RTK GPS定位

## 许可证

[根据项目需求填写]

## 联系方式

- 项目维护者：[your-email]
- Issues：[GitHub Issues链接]

---

**相关链接**：
- [STM32固件文档](CampusCar_STM32H723VGT6/README.md)
- [技术文档目录](docs/)
- [ROS2工作空间](nuc/robot/ros2_workspace_src/)
