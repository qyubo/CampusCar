# CyberLuban (鲁班) - 智能路面巡检机器人系统

<div align="center">

**基于 ROS2 的多传感器融合自主路面巡检与缺陷预测平台**

[![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue)](https://docs.ros.org/en/humble/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green)](https://www.python.org/)
[![Ubuntu 22.04](https://img.shields.io/badge/Ubuntu-22.04-orange)](https://ubuntu.com/)

[快速开始](#-快速开始) • [硬件平台](#-硬件平台) • [系统架构](#-系统架构) • [文档](#-文档导航)

</div>

---

> **📌 项目状态说明**  
> 本项目正在进行目录结构重构，以符合 ROS2 社区最佳实践。当前包名使用 `cri_*` 前缀（CampusRoadInspection 缩写），计划重构为更清晰的 `pavement_*` 命名。详见 [RESTRUCTURE_PLAN.md](RESTRUCTURE_PLAN.md)。

---

## 📋 目录

- [项目简介](#-项目简介)
- [硬件平台](#-硬件平台)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
- [软件模块](#-软件模块)
  - [驱动层](#1-驱动层-hardware-drivers)
  - [感知层](#2-感知层-perception)
  - [算法层](#3-算法层-analytics--algorithms)
  - [导航控制](#4-导航与控制-navigation--control)
  - [仿真环境](#5-仿真环境-simulation)
- [配置与标定](#-配置与标定)
- [文档导航](#-文档导航)
- [开发指南](#-开发指南)
- [常见问题](#-常见问题)

---

## 🎯 项目简介

**CyberLuban** 是一个完整的智能路面巡检机器人系统，集成了**硬件平台**、**ROS2 软件栈**、**AI 视觉检测**和**缺陷演化预测**。系统能够：

- 🚗 **自主巡检**：沿预设 GPS 航点自主行驶，实时避障
- 👁️ **多传感器感知**：RGBD 相机 + 激光雷达 + RTK GPS，厘米级定位
- 🔍 **缺陷检测**：YOLOv8 实时检测路面裂缝、坑洞、凹陷等病害
- 📍 **地理定位**：将检测到的缺陷精确映射到 GPS 经纬度坐标
- 📊 **演化预测**：基于历史数据预测缺陷发展趋势，评估风险等级
- 🗺️ **动态地图**：构建多层数字路面地图（高程/缺陷/风险）
- 🎮 **虚实孪生**：UE5 仿真环境，支持算法验证和可视化

### 应用场景

| 场景 | 说明 |
|------|------|
| 🏫 **校园道路** | 校园路面自动巡检，生成维护报告 |
| 🏢 **园区管理** | 工业园区、小区路面质量监控 |
| 🛣️ **市政养护** | 辅助市政部门路面巡检和养护规划 |
| 🔬 **科研平台** | 路面病害检测、传感器融合、预测建模研究 |

---

## 🤖 硬件平台

### 传感器配置

| 传感器 | 型号 | 功能 | 接口 |
|--------|------|------|------|
| **RGBD 相机** | Orbbec Gemini 336L | 彩色图 + 深度图，路面缺陷检测与避障 | USB 3.0 |
| **RTK GPS** | 千寻 NTRIP | 厘米级定位（差分定位） | UART |
| **激光雷达** | Livox Mid-360 | 360° 点云，障碍物检测 | Ethernet |
| **IMU** | 内置于底盘 | 姿态角（roll/pitch/yaw） | CAN / UART |

### 计算与控制单元

| 组件 | 型号/配置 | 功能 |
|------|-----------|------|
| **主控计算机** | Intel NUC 11 (i7-11代) | ROS2 节点运行、AI 推理（OpenVINO） |
| **底盘控制器** | STM32H723VGT6 | 电机控制、速度闭环、CAN 通信 |
| **操作系统** | Ubuntu 22.04 LTS | ROS2 Humble 基础环境 |

### 底盘平台

- **驱动方式**：差速驱动（双轮独立控制）
- **最大速度**：1.2 m/s
- **通信协议**：UART（ROS2 ↔ STM32）
- **供电**：24V 锂电池

> 📖 **详细硬件文档**：[docs/orbbec_defect_operation.md](docs/orbbec_defect_operation.md)  
> 🔧 **接线与组装**：参考 `hardware/stm32_chassis/` 目录

---

## 🏗️ 系统架构

### 分层架构

```
┌──────────────────────────────────────────────────────────────┐
│                    应用层 (Application)                        │
│  • 缺陷演化预测  • 动态地图生成  • 航点跟随  • 避障决策       │
└──────────────────────────────────────────────────────────────┘
                              ↑
┌──────────────────────────────────────────────────────────────┐
│                    算法层 (Analytics)                          │
│  • 低秩动力学世界模型  • 缺陷地理定位  • 风险评估             │
└──────────────────────────────────────────────────────────────┘
                              ↑
┌──────────────────────────────────────────────────────────────┐
│                    感知层 (Perception)                         │
│  • 视觉缺陷检测 (YOLOv8)  • 激光点云处理  • 传感器融合        │
└──────────────────────────────────────────────────────────────┘
                              ↑
┌──────────────────────────────────────────────────────────────┐
│                    驱动层 (Drivers)                            │
│  • Orbbec 相机驱动  • RTK GPS 驱动  • 底盘驱动  • 雷达驱动    │
└──────────────────────────────────────────────────────────────┘
                              ↑
┌──────────────────────────────────────────────────────────────┐
│                    硬件层 (Hardware)                           │
│  • RGBD 相机  • RTK GPS  • 激光雷达  • STM32 底盘             │
└──────────────────────────────────────────────────────────────┘
```

### ROS2 工作空间结构

```
nuc/robot/ros2_workspace_src/
├── src/                                # ROS2 包源代码
│   ├── cri_drivers/                   # 驱动层包组 ⚠️ 计划重命名为 pavement_drivers
│   │   ├── hikrobot_camera/          # Orbbec 相机驱动 ⚠️ 计划重命名
│   │   ├── rtk_gps_driver/           # RTK GPS 驱动
│   │   ├── chassis_driver/           # 底盘驱动（STM32 通信）
│   │   └── livox_driver/             # Livox 激光雷达驱动
│   │
│   ├── cri_perception/               # 感知层包组 ⚠️ 计划重命名为 pavement_perception
│   │   ├── vision_defect_detector/   # YOLOv8 视觉检测
│   │   ├── lidar_defect_detector/    # 激光点云处理
│   │   └── sensor_fusion/            # 传感器融合（地理定位+避障）
│   │
│   ├── cri_algorithm/                # 算法层包组 ⚠️ 计划重命名为 pavement_analytics
│   │   ├── world_model/              # 低秩动力学世界模型
│   │   └── dynamic_roadmap/          # 动态数字路面地图 + 航点跟随
│   │
│   ├── cri_msgs/                     # 消息定义 ⚠️ 计划重命名为 pavement_interfaces
│   ├── cri_bringup/                  # 启动配置 ⚠️ 计划重命名为 pavement_bringup
│   ├── cri_gazebo/                   # Gazebo 仿真 ⚠️ 计划重命名
│   └── ue5_bridge/                   # UE5 虚拟仿真桥接
│
├── config/                            # 全局配置文件
├── scripts/                           # 工具脚本（启动/标定/部署）
├── build/                             # 构建目录（Git 忽略）
├── install/                           # 安装目录（Git 忽略）
└── log/                               # 日志目录（Git 忽略）
```

> ⚠️ **命名说明**：当前包名使用 `cri_*` 前缀（CampusRoadInspection 缩写），语义不够明确。计划重构为 `pavement_*` 命名，详见 [RESTRUCTURE_PLAN.md](RESTRUCTURE_PLAN.md)

### 关键数据流

```
┌─────────────┐
│ Orbbec 相机  │ ──> /camera/color/image_raw ──┐
└─────────────┘                                │
                                               ↓
┌─────────────┐                      ┌─────────────────────┐
│  RTK GPS    │ ──> /fix ──────────> │  视觉缺陷检测节点    │
└─────────────┘                      └─────────────────────┘
                                               ↓
┌─────────────┐                      /perception/vision_defects
│ 相机方向控制 │ ──> /camera_direction         ↓
└─────────────┘                      ┌─────────────────────┐
                                     │ 缺陷地理定位节点     │ ──> /perception/geolocated_defects
                                     └─────────────────────┘
                                               ↓
                                     ┌─────────────────────┐
                                     │ 缺陷演化评估节点     │ ──> /analytics/defect_evolution
                                     └─────────────────────┘
                                               ↓
                                     ┌─────────────────────┐
                                     │ 动态地图生成节点     │ ──> /map/digital_roadmap
                                     └─────────────────────┘

┌─────────────┐
│ 深度图       │ ──> /camera/depth/image_raw ──> 避障节点 ──> /cmd_vel_safe
└─────────────┘

┌─────────────┐
│ 固定航点     │ ──> 航点跟随节点 ──> /cmd_vel ──> 避障节点 ──> 底盘驱动
└─────────────┘
```

---

## 🚀 快速开始

### 环境要求

| 项目 | 要求 |
|------|------|
| **操作系统** | Ubuntu 22.04 LTS |
| **ROS2 版本** | Humble Hawksbill |
| **Python** | 3.10+ |
| **CUDA**（可选） | 11.8+（用于 GPU 加速推理） |

### 安装步骤

#### 1. 安装 ROS2 Humble

```bash
# 添加 ROS2 官方源
sudo apt update && sudo apt install software-properties-common
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 安装 ROS2 Humble
sudo apt update
sudo apt install ros-humble-desktop
```

#### 2. 安装依赖

```bash
# 安装 Python 依赖
pip install opencv-python numpy pyorbbecsdk ultralytics openvino scipy

# 安装 Colcon 构建工具
sudo apt install python3-colcon-common-extensions

# 安装传感器驱动依赖
sudo apt install ros-humble-sensor-msgs ros-humble-cv-bridge
```

#### 3. 构建工作空间

```bash
cd /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src

# 构建所有包
colcon build --symlink-install

# Source 环境
source install/setup.bash
```

### 一键启动

#### 方式一：分层启动（推荐调试时使用）

```bash
# 终端 1：启动驱动层
ros2 launch cri_bringup drivers.launch.py

# 终端 2：启动感知层
ros2 launch cri_bringup perception.launch.py

# 终端 3：启动算法层
ros2 launch cri_bringup algorithms.launch.py
```

#### 方式二：一键启动全部节点

```bash
ros2 launch cri_bringup full_system.launch.py
```

#### 方式三：使用便捷脚本（Orbbec 相机 + 视觉检测）

```bash
# 启动相机和缺陷检测
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh start

# 查看状态
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh status

# 停止服务
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh stop
```

### 验证系统

#### 查看话题

```bash
# 查看所有活跃话题
ros2 topic list

# 查看相机图像（应有数据发布）
ros2 topic hz /camera/color/image_raw

# 查看检测结果
ros2 topic echo /perception/vision_defects
```

#### 可视化工具

```bash
# RViz2 可视化
ros2 run rviz2 rviz2

# RQT 图形界面
rqt
```

#### Web 界面（实时图像）

- **原始相机画面**：http://localhost:8088/
- **缺陷检测结果**：http://localhost:8089/

---

## 📦 软件模块

### 1. 驱动层 (Hardware Drivers)

#### 1.1 Orbbec RGBD 相机驱动

**包名**：`cri_drivers/hikrobot_camera` ⚠️ *计划重命名为* `pavement_drivers/orbbec_camera_driver`

**功能**：
- 发布彩色图像 `/camera/color/image_raw`（640×480 @ 30fps）
- 发布深度图像 `/camera/depth/image_raw`（用于避障）
- 发布相机内参 `/camera/color/camera_info`

**关键文件**：
- 节点：`orbbec_camera_node.py`
- 配置：`config/orbbec_camera_config.yaml`

**使用**：
```bash
ros2 run hikrobot_camera orbbec_camera_node
```

#### 1.2 RTK GPS 驱动

**包名**：`cri_drivers/rtk_gps_driver`

**功能**：
- 接收千寻 NTRIP 差分数据
- 发布 GPS 定位 `/fix`（NavSatFix，厘米级精度）
- 支持 RTK 固定解状态监控

**关键文件**：
- 节点：`rtk_gps_node.py`
- 配置：`config/rtk_gps_params.yaml`（包含 NTRIP 账号密码）

**使用**：
```bash
ros2 run rtk_gps_driver rtk_gps_node
```

#### 1.3 底盘驱动

**包名**：`cri_drivers/chassis_driver`

**功能**：
- 订阅速度指令 `/cmd_vel_safe`（经过避障调整后）
- 通过 UART 与 STM32 通信
- 发布里程计 `/odom`（编码器反馈）

**关键文件**：
- 节点：`chassis_driver_node.py`
- STM32 固件：`hardware/stm32_chassis/firmware/`

**使用**：
```bash
ros2 run chassis_driver chassis_driver_node
```

#### 1.4 Livox 激光雷达驱动

**包名**：`cri_drivers/livox_driver`

**功能**：
- 发布点云数据 `/livox/lidar`（PointCloud2）
- 360° 扫描，用于障碍物检测和建图

**使用**：
```bash
ros2 launch livox_driver livox.launch.py
```

---

### 2. 感知层 (Perception)

#### 2.1 视觉缺陷检测

**包名**：`cri_perception/vision_defect_detector`

**功能**：
- 订阅相机图像 `/camera/color/image_raw`
- 使用 YOLOv8 + OpenVINO 实时检测路面缺陷
- 检测类别：裂缝（D00/D10/D20）、坑洞（D40）、凹陷等
- 发布检测结果 `/perception/vision_defects`（DefectInfo 消息）
- 发布标注图像 `/perception/detection_image`

**关键文件**：
- 节点：`vision_defect_detector_node.py`
- 模型：`models/yolov8/pavement_defect.pt`（训练好的权重）
- 配置：`config/detector_params.yaml`

**使用**：
```bash
ros2 run vision_defect_detector vision_defect_detector_node
```

**性能**：
- 推理速度：~30 FPS（OpenVINO FP16）
- 检测精度：mAP@0.5 = 0.85+

#### 2.2 激光雷达障碍物检测

**包名**：`cri_perception/lidar_defect_detector`

**功能**：
- 订阅激光雷达点云 `/livox/lidar`
- 提取地面点云和障碍物点云
- 发布障碍物信息（用于多传感器融合）

**关键文件**：
- 节点：`lidar_obstacle_detector_node.py`

#### 2.3 传感器融合

**包名**：`cri_perception/sensor_fusion`

**功能**：

**2.3.1 缺陷地理定位节点** (`defect_geolocation_node.py`)
- 订阅视觉检测结果 `/perception/vision_defects`
- 订阅 GPS 位置 `/fix`
- 订阅相机方向 `/camera_direction`（left/medium/right）
- **像素 → 地面投影 → GPS 经纬度**转换
- 估算缺陷实际尺寸（长×宽，单位：米）
- 发布地理定位结果 `/perception/geolocated_defects`

**关键算法**：
```
1. 像素坐标去畸变
2. 构造射线（相机坐标系）
3. 射线与地面平面求交
4. 地面坐标 → 机器人坐标系（外参变换）
5. 机器人坐标 + GPS → 缺陷 GPS 坐标
```

**配置**：`config/geolocation_params.yaml`（三档位外参标定）

**2.3.2 深度避障节点** (`obstacle_avoidance_node.py`)
- 订阅深度图 `/camera/depth/image_raw`
- 订阅原始速度指令 `/cmd_vel`
- 发布安全速度指令 `/cmd_vel_safe`（避障调整后）
- **三级避障策略**：
  - 危险区（< 0.5m）：立即停止
  - 警戒区（0.5-1.0m）：减速至 50%
  - 安全区（> 1.0m）：正常通过

---

### 3. 算法层 (Analytics & Algorithms)

#### 3.1 低秩动力学世界模型

**包名**：`cri_algorithm/world_model`

**功能**：
- 基于 **SVD 降维 + Paris 疲劳定律**建模路面缺陷演化
- 输入：历史缺陷观测数据矩阵（时间×空间）
- 输出：低秩表示 + 演化速率场

**关键算法**：
```
X ≈ U Σ V^T  (SVD 分解)
dS/dN = C (ΔK)^m  (Paris 定律)
```

**关键文件**：
- 节点：`world_model_node.py`
- 配置：`config/world_model_params.yaml`

**参考文档**：[docs/algorithms/world_model.md](docs/campus_road_inspection_ws/docs/PACKAGE_STRUCTURE.md)

#### 3.2 缺陷演化评估

**包名**：`cri_algorithm/world_model`（子模块：`defect_evolution_node.py`）

**功能**：
- 订阅地理定位缺陷 `/perception/geolocated_defects`
- **地理聚类**：2m 半径内的缺陷认为是同一个
- 维护观测历史（timestamp, 尺寸, GPS 坐标）
- **演化模型拟合**：
  - 线性增长：`size(t) = size_0 + rate × t`
  - 指数增长：`size(t) = size_0 × exp(k × t)`
- **风险评估**：safe / low / medium / high / critical
- 预测 7 天 / 30 天后的缺陷尺寸
- 发布演化评估结果 `/analytics/defect_evolution`

**关键文件**：
- 节点：`defect_evolution_node.py`
- 配置：`config/evolution_params.yaml`

**风险等级判断**：
| 风险等级 | 当前面积 | 演化速率 | 预测 30 天面积 |
|----------|----------|----------|----------------|
| safe | < 0.01 m² | < 0.001 m²/天 | < 0.05 m² |
| low | 0.01-0.05 m² | 0.001-0.005 m²/天 | 0.05-0.1 m² |
| medium | 0.05-0.1 m² | 0.005-0.01 m²/天 | 0.1-0.2 m² |
| high | 0.1-0.3 m² | 0.01-0.02 m²/天 | 0.2-0.5 m² |
| critical | > 0.3 m² | > 0.02 m²/天 | > 0.5 m² |

#### 3.3 动态数字路面地图

**包名**：`cri_algorithm/dynamic_roadmap`

**功能**：
- 订阅缺陷演化评估 `/analytics/defect_evolution`
- 构建多层栅格地图：
  - **高程层**：路面高度（激光雷达）
  - **材质层**：沥青/混凝土/砖石
  - **缺陷层**：缺陷位置和类型
  - **风险层**：风险等级热力图
  - **预测层**：未来演化趋势
- 增量更新（新观测自动融合）
- 发布地图 `/map/digital_roadmap`

**关键文件**：
- 节点：`digital_roadmap_node.py`
- 配置：`config/roadmap_params.yaml`

---

### 4. 导航与控制 (Navigation & Control)

#### 4.1 固定航点跟随

**包名**：`cri_algorithm/dynamic_roadmap`（子模块：`fixed_waypoint_follower_node.py`）

**功能**：
- 订阅 RTK 位置 `/fix`
- 读取固定 GPS 航点列表（配置文件）
- **Haversine 距离**计算到下一航点的距离
- 航向估计（基于 GPS 轨迹）
- 发布速度指令 `/cmd_vel`（前向速度 + 角速度）
- 到达阈值：2 米

**关键文件**：
- 节点：`fixed_waypoint_follower_node.py`
- 配置：`config/waypoints.yaml`（航点列表）

**航点格式示例**：
```yaml
waypoints:
  - {latitude: 31.234567, longitude: 121.654321}
  - {latitude: 31.234580, longitude: 121.654340}
  - {latitude: 31.234595, longitude: 121.654360}
```

#### 4.2 深度避障

已在感知层介绍（`sensor_fusion/obstacle_avoidance_node.py`），详见 [2.3.2](#23-传感器融合)

---

### 5. 仿真环境 (Simulation)

#### 5.1 Gazebo 仿真

**包名**：`cri_gazebo`

**功能**：
- 提供校园道路场景
- 仿真传感器（相机/激光雷达/GPS）
- 用于算法开发和测试

**启动**：
```bash
ros2 launch cri_gazebo campus_world.launch.py
```

#### 5.2 UE5 虚拟仿真

**包名**：`ue5_bridge`

**功能**：
- 高保真视觉渲染
- 真实物理引擎
- ROS2 ↔ UE5 双向通信
- 虚实孪生验证

**启动**：
```bash
ros2 launch ue5_bridge ue5_bridge.launch.py
```

**参考文档**：[docs/campus_road_inspection_ws/docs/UE5_BRIDGE.md](docs/campus_road_inspection_ws/docs/UE5_BRIDGE.md)

---

## ⚙️ 配置与标定

### 相机外参标定

系统支持三个舵机档位（left/medium/right），每个档位需单独标定外参。

#### 使用交互式标定脚本

```bash
cd /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src
python3 scripts/calibrate_camera_extrinsic.py
```

#### 手动配置

编辑 `sensor_fusion/config/geolocation_params.yaml`：

```yaml
servo_pose_tfs_json: '{
  "left":   [x, y, z, roll, pitch, yaw],
  "medium": [x, y, z, roll, pitch, yaw],
  "right":  [x, y, z, roll, pitch, yaw]
}'
```

- `x, y, z`：相机相对机器人中心的位置（米）
- `roll, pitch, yaw`：相机姿态角（ZYX 欧拉角，度）

### RTK 差分配置

编辑 `rtk_gps_driver/config/rtk_gps_params.yaml`：

```yaml
ntrip_server: "ntrip.qxwz.com"
ntrip_port: 8002
ntrip_mountpoint: "AUTO"
ntrip_username: "your_username"
ntrip_password: "your_password"
```

### 更多配置

| 配置文件 | 说明 |
|----------|------|
| `geolocation_params.yaml` | 地理定位参数（内参/外参） |
| `detector_params.yaml` | 视觉检测模型参数（置信度阈值） |
| `evolution_params.yaml` | 演化评估参数（聚类半径、风险阈值） |
| `waypoints.yaml` | 固定航点列表 |
| `obstacle_avoidance_params.yaml` | 避障参数（安全距离） |

---

## 📚 文档导航

### 用户指南

| 文档 | 说明 |
|------|------|
| [快速启动](docs/guides/quickstart.md) | 安装和快速上手 |
| [Orbbec 相机操作](docs/orbbec_defect_operation.md) | 相机启动、可视化、故障排查 |
| [硬件组装](hardware/stm32_chassis/README.md) | 底盘接线和调试 |

### 开发者指南

| 文档 | 说明 |
|------|------|
| [系统架构](docs/architecture/system_overview.md) | 完整技术架构 |
| [包结构说明](docs/campus_road_inspection_ws/docs/PACKAGE_STRUCTURE.md) | ROS2 包详细说明 |
| [重构计划](RESTRUCTURE_PLAN.md) | 目录重组和命名规范 |

### 算法原理

| 文档 | 说明 |
|------|------|
| 低秩动力学世界模型 | SVD + Paris 定律（详见 README 3.1 节） |
| 缺陷演化评估 | 地理聚类 + 演化建模（详见 README 3.2 节） |
| 传感器融合 | 像素-地面-GPS 转换（详见 README 2.3 节） |

### 硬件文档

| 文档 | 说明 |
|------|------|
| [STM32 固件](hardware/stm32_chassis/firmware/) | 底盘控制器代码 |
| [WASD 测试指南](docs/chassis/CampusCar_STM32H723VGT6/WASD_TEST_GUIDE.md) | 底盘手动控制测试 |

---

## 🛠️ 开发指南

### 构建工作空间

```bash
cd /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src

# 完整构建
colcon build --symlink-install

# 仅构建特定包
colcon build --packages-select cri_perception

# 构建包及其依赖
colcon build --packages-up-to vision_defect_detector
```

### 代码风格

- **Python**：遵循 PEP 8
- **ROS2 节点**：使用面向对象风格，继承 `rclpy.node.Node`
- **命名规范**：
  - 包名：`小写_下划线`
  - 节点：`功能_node.py`
  - 话题：`/命名空间/功能/数据类型`

### 测试

```bash
# 运行 Python 单元测试
colcon test --packages-select vision_defect_detector

# 查看测试结果
colcon test-result --verbose
```

### 贡献流程

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "Add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 Pull Request

---

## ❓ 常见问题

### 1. 相机无法启动

**症状**：`orbbec_camera_node` 报错 "Failed to open device"

**解决**：
```bash
# 检查 USB 设备
lsusb | grep Orbbec

# 添加 USB 权限
sudo usermod -a -G plugdev $USER
sudo reboot
```

### 2. RTK 无固定解

**症状**：GPS 精度不足（未达到厘米级）

**解决**：
- 检查 NTRIP 账号密码是否正确
- 确保天线放置在开阔区域（无遮挡）
- 等待 5-10 分钟达到固定解状态

### 3. 视觉检测无输出

**症状**：`/perception/vision_defects` 话题无数据

**解决**：
```bash
# 检查相机图像
ros2 topic hz /camera/color/image_raw

# 查看检测节点日志
ros2 node info /vision_defect_detector
```

### 4. 底盘不响应速度指令

**症状**：发布 `/cmd_vel` 但底盘不动

**解决**：
- 检查串口连接：`ls /dev/ttyUSB*`
- 检查 STM32 固件是否正常
- 验证速度指令：`ros2 topic echo /cmd_vel_safe`

### 5. 编译错误

**症状**：`colcon build` 失败

**解决**：
```bash
# 清理构建缓存
rm -rf build install log

# 重新构建
colcon build --symlink-install
```

---

## 📄 许可证

本项目采用 **MIT License** 开源。详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- **ROS2 社区**：提供强大的机器人操作系统框架
- **Orbbec**：提供 RGBD 相机 SDK
- **Ultralytics**：YOLOv8 目标检测框架
- **OpenVINO**：高性能 AI 推理工具包

---

## 📮 联系方式

如有问题或建议，欢迎通过以下方式联系：

- **GitHub Issues**：提交 Bug 或功能请求
- **Email**：qyb413@example.com

---

<div align="center">

**🚀 让路面巡检更智能！**

[⬆ 回到顶部](#cyberluban-鲁班---智能路面巡检机器人系统)

</div>
