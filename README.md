# CampusCar - 校园巡检机器人

基于 ROS2 的智能校园巡检机器人系统，集成 RGBD 视觉缺陷检测、底盘运动控制、深度避障、RTK 定位等功能。

## 🎯 核心功能

- **视觉缺陷检测**：Orbbec RGBD 相机 + YOLOv8 + OpenVINO 加速
- **缺陷地理定位**：深度图优先 + 单目投影兜底，三档相机外参（left/medium/right）
- **缺陷拍照记录**：自动触发拍照，保存原图、检测图和元数据，Web 展示（端口 8090）
- **深度避障**：实时深度图分析，输出安全速度命令
- **底盘控制**：STM32 驱动，支持速度、舵机、灯光控制
- **实时监控**：相机原始画面（8088）、检测结果画面（8089）

## 📁 仓库结构

```
CyberLuban/
├── campusCar-hardware-new-stm32-hikrobot/  # STM32 底盘固件（海康相机版本）
├── CampusCar_STM32H723VGT6/                # STM32 底盘固件（最新版本，不上传）
├── campus_road_inspection_ws/              # ROS2 巡检工作空间（归档）
├── chassis/                                # 底盘代码归档
│   └── CampusCar_STM32H723VGT6/           # STM32 固件历史版本
├── nuc/                                    # NUC 上位机代码和工具
│   ├── robot/                             # 当前开发工作空间
│   │   ├── ros2_workspace_src/            # ROS2 工作空间（感知融合、底盘驱动）
│   │   ├── defect_recording_web.py        # 缺陷记录 Web 服务（8090）
│   │   └── recording/                     # 缺陷拍照保存目录
│   ├── robot_archive/                     # 历史归档工作空间
│   ├── campus_road_inspection_ws/         # 早期巡检工作空间
│   ├── brain/                             # UE5 数字孪生相关
│   └── tools/                             # 工具脚本
├── docs/                                   # 文档中心
│   ├── orbbec_defect_operation.md         # Orbbec 实车操作完整文档 ⭐
│   ├── FINAL_REPORT.md                    # 项目最终报告
│   ├── REPOSITORY_CLEANUP_20260823.md     # 仓库整理报告
│   ├── guides/                            # 操作指南
│   ├── architecture/                      # 架构设计
│   └── chassis/                           # 底盘文档
├── calibration_images/                     # 相机标定图像
├── datasets/                               # 训练数据集（不上传）
└── 各项说明/                               # 串口协议、开发文档等

```

## 🚀 快速开始

### 1. Orbbec 视觉缺陷检测（推荐）

完整的视觉检测和避障系统。

```bash
# 进入 ROS2 工作空间
cd ~/CyberLuban/nuc/robot/ros2_workspace_src

# 一键启动（相机 + 检测 + 避障 + Web）
./scripts/orbbec_defect_control.sh start

# 查看实时画面
# 原始相机画面：http://<NUC_IP>:8088
# 检测结果画面：http://<NUC_IP>:8089
# 缺陷记录展示：http://<NUC_IP>:8090

# 停止所有服务
./scripts/orbbec_defect_control.sh stop
```

**详细说明**：[docs/orbbec_defect_operation.md](docs/orbbec_defect_operation.md)

### 2. 底盘控制

```bash
# 底盘驱动节点
ros2 run chassis_driver chassis_driver_node

# 手动控制
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.0}}"

# 舵机控制（三档位置）
ros2 topic pub /camera_direction std_msgs/msg/String "data: 'medium'"  # left/medium/right
```

### 3. 串口协议说明

详见 [各项说明/STM32-NUC_10字节串口协议规范_v1.0.md](各项说明/STM32-NUC_10字节串口协议规范_v1.0.md)

## 📡 关键 ROS2 话题

| 话题名称 | 类型 | 说明 |
|---------|------|------|
| `/cmd_vel` | `Twist` | 底盘速度控制指令 |
| `/cmd_vel_safe` | `Twist` | 避障后的安全速度 |
| `/camera_direction` | `String` | 舵机方向（right/medium/left）|
| `/camera/color/image_raw` | `Image` | Orbbec 彩色图 |
| `/camera/depth/image_raw` | `Image` | Orbbec 深度图 |
| `/perception/detection_image` | `Image` | 缺陷检测标注图 |
| `/perception/vision_defects` | `VisionDefectArray` | 检测到的缺陷列表 |
| `/perception/geolocated_defects` | `GeolocatedDefectArray` | 地理定位后的缺陷 |
| `/chassis/status` | `ChassisStatus` | 底盘状态反馈 |

## 📚 推荐阅读顺序

1. [本 README](README.md) - 了解项目整体结构
2. [Orbbec 实车操作文档](docs/orbbec_defect_operation.md) - 掌握视觉检测系统
3. [仓库整理报告](docs/REPOSITORY_CLEANUP_20260823.md) - 了解最近的整理内容
4. [串口协议规范](各项说明/STM32-NUC_10字节串口协议规范_v1.0.md) - STM32-NUC 通信协议
5. [项目最终报告](docs/FINAL_REPORT.md) - 项目完整总结

## 🛠️ 技术栈

- **ROS2 Humble** - 机器人操作系统
- **Orbbec RGBD 相机** - 深度视觉感知
- **YOLOv8** - 缺陷检测模型
- **OpenVINO** - AI 推理加速
- **STM32H723VGT6** - 底盘嵌入式控制
- **Flask** - Web 展示服务
- **Python 3** - 上位机开发语言

## 📝 开发说明

- **活跃开发目录**：`nuc/robot/ros2_workspace_src/`
- **历史归档目录**：`nuc/robot_archive/`、`campus_road_inspection_ws/`
- **不上传目录**：`CampusCar_STM32H723VGT6/`（已在 .gitignore 中排除）

## 📅 最近更新

- **2026-08-23**：完成仓库整理，删除重复代码副本，补充 Orbbec 缺陷检测文档
- **2026-08-22**：完成 Orbbec 缺陷检测、地理定位、拍照记录功能
- **2026-08-21**：实现深度避障和缺陷触发拍照

---

**项目维护**：CyberLuban Team | **最后更新**：2026-08-23

