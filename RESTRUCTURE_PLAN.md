# CyberLuban 项目重构方案（2026-08-23）

> **重要**: 本次重构基于GitHub高星ROS2项目最佳实践，目标是建立清晰、标准、易维护的项目结构。

## 一、当前问题分析

### 1.1 目录结构问题
- **不符合ROS2标准**：`nuc/robot/ros2_workspace_src` 命名混乱
- **语义不明确**：`cri_*` 前缀含义模糊（CampusRoadInspection缩写）
- **硬件/软件混杂**：STM32、底盘代码与ROS2工作空间混在一起
- **文档分散**：docs目录结构混乱，archive内容重复
- **中文目录名**：`各项说明` 不符合开源规范

### 1.2 包命名问题
- `cri_drivers` → 应明确为 `pavement_drivers`
- `cri_perception` → 应明确为 `pavement_perception`
- `cri_algorithm` → 应明确为 `pavement_analytics`
- `cri_msgs` → 应明确为 `pavement_interfaces`（ROS2约定）
- `cri_bringup` → 应明确为 `pavement_bringup`
- `cri_gazebo` → 应明确为 `pavement_simulation`

---

## 二、新目录结构设计（参考Navigation2等高星项目）

```
pavement_inspection_robot/              # 项目根目录（重命名）
│
├── README.md                            # 主文档（重写）
├── LICENSE                              # 开源许可
├── .gitignore                          # Git忽略规则
│
├── ros2_ws/                            # ROS2标准工作空间（重命名）
│   ├── src/                            # 源代码（唯一需要Git追踪）
│   │   │
│   │   ├── pavement_drivers/          # 驱动层包组
│   │   │   ├── orbbec_camera_driver/  # 明确Orbbec相机
│   │   │   ├── rtk_gps_driver/
│   │   │   ├── chassis_driver/
│   │   │   └── livox_lidar_driver/    # 明确Livox激光雷达
│   │   │
│   │   ├── pavement_perception/       # 感知层包组
│   │   │   ├── vision_defect_detector/
│   │   │   ├── lidar_obstacle_detector/
│   │   │   └── sensor_fusion/
│   │   │
│   │   ├── pavement_analytics/        # 算法/分析层包组
│   │   │   ├── defect_evolution/      # 缺陷演化评估
│   │   │   ├── world_model/           # 低秩动力学世界模型
│   │   │   └── digital_roadmap/       # 动态数字路面地图
│   │   │
│   │   ├── pavement_navigation/       # 导航层包组（新增）
│   │   │   ├── waypoint_follower/     # 固定航点跟随
│   │   │   └── obstacle_avoidance/    # 深度避障
│   │   │
│   │   ├── pavement_interfaces/       # 消息/服务/动作定义
│   │   │   ├── msg/
│   │   │   ├── srv/
│   │   │   └── action/
│   │   │
│   │   ├── pavement_description/      # 机器人描述（URDF/Xacro）
│   │   │   ├── urdf/
│   │   │   ├── meshes/
│   │   │   └── config/
│   │   │
│   │   ├── pavement_bringup/          # 启动配置
│   │   │   ├── launch/
│   │   │   └── config/
│   │   │
│   │   └── pavement_simulation/       # 仿真（Gazebo/UE5）
│   │       ├── gazebo/
│   │       ├── ue5_bridge/
│   │       └── worlds/
│   │
│   ├── build/                          # 构建目录（Git忽略）
│   ├── install/                        # 安装目录（Git忽略）
│   └── log/                            # 日志目录（Git忽略）
│
├── hardware/                           # 硬件相关（嵌入式/电路）
│   ├── stm32_chassis/                 # STM32底盘控制器
│   │   ├── firmware/
│   │   ├── docs/
│   │   └── README.md
│   │
│   └── electronics/                    # 电路设计/原理图
│       └── README.md
│
├── datasets/                           # 数据集
│   ├── defect_images/                 # 缺陷图像训练集
│   ├── calibration/                   # 标定数据
│   └── field_test/                    # 实地测试数据
│
├── models/                             # AI模型
│   ├── yolov8/                        # 视觉检测模型
│   ├── openvino/                      # 优化后模型
│   └── README.md
│
├── docs/                               # 文档（重组）
│   ├── user_guide/                    # 用户指南
│   │   ├── quick_start.md
│   │   ├── installation.md
│   │   └── operation.md
│   │
│   ├── developer_guide/               # 开发者指南
│   │   ├── architecture.md
│   │   ├── api_reference.md
│   │   └── contributing.md
│   │
│   ├── hardware/                      # 硬件文档
│   │   ├── assembly.md
│   │   ├── calibration.md
│   │   └── wiring.md
│   │
│   ├── algorithms/                    # 算法原理
│   │   ├── world_model.md
│   │   ├── defect_evolution.md
│   │   └── sensor_fusion.md
│   │
│   └── media/                         # 图片/视频资源
│       ├── images/
│       └── videos/
│
├── scripts/                            # 工具脚本
│   ├── setup_environment.sh
│   ├── build_workspace.sh
│   ├── calibrate_camera.py
│   └── deploy_robot.sh
│
└── tools/                              # 开发工具
    ├── data_visualization/
    ├── log_analysis/
    └── testing/
```

---

## 三、包重命名映射表

| 旧包名 | 新包名 | 变更原因 |
|--------|--------|----------|
| `cri_drivers/hikrobot_camera` | `pavement_drivers/orbbec_camera_driver` | 明确Orbbec品牌，driver后缀 |
| `cri_drivers/rtk_gps_driver` | `pavement_drivers/rtk_gps_driver` | 前缀统一 |
| `cri_drivers/chassis_driver` | `pavement_drivers/chassis_driver` | 前缀统一 |
| `cri_drivers/livox_driver` | `pavement_drivers/livox_lidar_driver` | 明确Livox激光雷达 |
| `cri_perception/vision_defect_detector` | `pavement_perception/vision_defect_detector` | 前缀统一 |
| `cri_perception/lidar_defect_detector` | `pavement_perception/lidar_obstacle_detector` | 明确避障用途 |
| `cri_perception/sensor_fusion` | `pavement_perception/sensor_fusion` | 前缀统一 |
| `cri_algorithm/world_model` | `pavement_analytics/world_model` | algorithm→analytics |
| `cri_algorithm/dynamic_roadmap` | `pavement_analytics/digital_roadmap` | 更清晰的名称 |
| 新增（从sensor_fusion分离） | `pavement_analytics/defect_evolution` | 独立演化评估模块 |
| 新增（从dynamic_roadmap分离） | `pavement_navigation/waypoint_follower` | 独立导航模块 |
| 新增（从sensor_fusion分离） | `pavement_navigation/obstacle_avoidance` | 独立避障模块 |
| `cri_msgs` | `pavement_interfaces` | 符合ROS2约定 |
| `cri_bringup` | `pavement_bringup` | 前缀统一 |
| `cri_gazebo` | `pavement_simulation` | 更通用名称 |
| `ue5_bridge` | `pavement_simulation/ue5_bridge` | 合并到仿真包组 |

---

## 四、命名规范（基于ROS2社区最佳实践）

### 4.1 包命名规则
- **格式**：`小写字母_下划线分隔`
- **前缀**：`pavement_` 表示路面巡检项目域
- **标准后缀**：
  - `_driver` / `_drivers`: 硬件驱动
  - `_detector`: 检测算法
  - `_interfaces`: 消息/服务/动作定义（ROS2约定）
  - `_bringup`: 启动配置
  - `_simulation`: 仿真环境
  - `_description`: 机器人描述（URDF/Xacro）
  - `_navigation`: 导航相关
  - `_perception`: 感知相关
  - `_analytics`: 数据分析/算法

### 4.2 节点文件命名
- **格式**：`功能描述_node.py`
- **示例**：
  - `defect_geolocation_node.py` ✓
  - `obstacle_avoidance_node.py` ✓
  - `geo_loc.py` ✗（避免缩写）

### 4.3 Launch文件命名
- **描述性命名**：
  - `bringup_all_nodes.launch.py`（不是`full_system.launch.py`）
  - `drivers_all.launch.py`
  - `perception_all.launch.py`
  - `analytics_all.launch.py`

### 4.4 配置文件命名
- **对应节点**：`<node_name>_params.yaml`
- **硬件配置**：`<hardware>_config.yaml`
- **示例**：
  - `geolocation_params.yaml`
  - `orbbec_camera_config.yaml`
  - `robot_params.yaml`

### 4.5 话题命名
- **格式**：`/命名空间/功能/数据类型`
- **示例**：
  - `/camera/color/image_raw`
  - `/perception/defects`
  - `/navigation/waypoints`

### 4.6 目录命名
- 英文小写 + 下划线
- 避免缩写（除非约定俗成：`ros2_ws`, `docs`, `src`）
- 功能明确

---

## 五、实施步骤（分阶段）

### 阶段一：准备和备份 ✓
1. ✓ 创建本重构方案文档
2. 创建Git标签备份当前状态：`git tag v0-before-restructure`
3. 更新`.gitignore`

### 阶段二：顶层目录重组
1. 移动`nuc/robot/ros2_workspace_src` → `ros2_ws`
2. 合并STM32代码到`hardware/stm32_chassis/`
3. 移动训练集到`datasets/defect_images/`
4. 移动模型到`models/`
5. 删除中文目录`各项说明`（或重命名为`misc_notes`）

### 阶段三：ROS2包重命名
按照映射表逐个重命名包，每个包需要更新：
- 目录名
- `package.xml`中的`<name>`标签
- `setup.py`中的`name`字段
- 所有import语句

### 阶段四：文档重组
1. 按照新结构重组`docs/`目录
2. 删除冗余的`docs/archive/`内容（使用Git历史管理）
3. 合并分散的README

### 阶段五：更新所有引用
1. 所有launch文件中的包名引用
2. 所有Python代码的import语句
3. 所有文档中的路径引用
4. 配置文件中的命名空间

### 阶段六：重写README.md
按照新大纲（见下节）完全重写主README

### 阶段七：验证
1. `colcon build --symlink-install`测试编译
2. 运行各层启动文件验证
3. 检查所有文档链接有效性

---

## 六、README.md 新结构大纲（平衡所有内容）

### 内容分配原则
- **硬件 + 软件 = 约50/50**
- **驱动 + 感知 + 算法 + 导航 = 平衡**
- **实用性 > 理论深度**
- **README提供概览，详细内容链接到docs/**

### 章节规划

1. **项目简介**（15%）
   - 一句话描述
   - 核心功能列表
   - 应用场景
   - 技术亮点
   - 系统演示图/视频

2. **硬件平台**（12%）
   - 传感器清单（Orbbec相机/RTK GPS/Livox激光雷达）
   - 底盘平台（STM32控制器）
   - 计算单元（Intel NUC）
   - 硬件框架图
   - → 链接到`docs/hardware/assembly.md`

3. **系统架构**（13%）
   - 软件分层架构图
   - ROS2节点拓扑图
   - 数据流图
   - → 链接到`docs/developer_guide/architecture.md`

4. **快速开始**（12%）
   - 环境要求（Ubuntu 22.04 + ROS2 Humble）
   - 依赖安装
   - 工作空间构建
   - 一键启动命令
   - 验证测试
   - → 链接到`docs/user_guide/quick_start.md`

5. **ROS2包结构**（25%）
   - **驱动层**（6%）：Orbbec/RTK/底盘/激光雷达驱动简介
   - **感知层**（6%）：视觉检测/激光雷达/传感器融合简介
   - **算法层**（7%）：世界模型/演化评估/数字地图简介
   - **导航层**（6%）：航点跟随/深度避障简介
   - 每个包简要说明（1-2句）+ 链接到详细文档

6. **配置与标定**（8%）
   - 参数文件位置
   - 相机内外参标定流程
   - RTK差分配置
   - 常用配置项
   - → 链接到`docs/hardware/calibration.md`

7. **文档导航**（5%）
   - 用户指南
   - 开发者指南
   - 硬件文档
   - 算法原理文档

8. **开发指南**（5%）
   - 构建命令
   - 测试方法
   - 代码风格
   - 贡献流程

9. **常见问题**（3%）
   - 安装问题
   - 运行错误
   - 调试方法

10. **许可与引用**（2%）
    - 开源许可
    - 引用格式
    - 致谢

---

## 七、关键变更清单

### 新增内容
- `pavement_navigation/` 包组（独立导航功能）
- `pavement_description/` 包（URDF/机器人描述）
- `hardware/` 顶层目录（整合所有硬件代码）
- `models/` 顶层目录（AI模型独立管理）
- `scripts/` 顶层目录（工具脚本）
- `tools/` 顶层目录（开发工具）
- 重组后的`docs/`结构

### 移除/合并内容
- 删除`nuc/`顶层目录（工作空间移到顶层）
- 合并重复的STM32目录
- 删除`docs/archive/`冗余内容
- 删除或重命名`各项说明/`中文目录

### 重命名内容
- 所有`cri_*`包 → `pavement_*`
- `hikrobot_camera` → `orbbec_camera_driver`
- `livox_driver` → `livox_lidar_driver`
- `cri_msgs` → `pavement_interfaces`
- `dynamic_roadmap` → `digital_roadmap`

---

## 八、风险与缓解

### 风险1：大规模重命名导致编译失败
**缓解**：
- 使用Git标签备份
- 分包逐步重命名和测试
- 使用`colcon build --packages-select`单独测试

### 风险2：文档链接失效
**缓解**：
- 使用相对路径
- 重构后运行链接检查工具
- 逐步验证每个文档

### 风险3：历史代码丢失
**缓解**：
- 保持Git完整历史
- 使用`git mv`保留文件历史
- 不删除任何功能代码

---

## 九、参考资源

### ROS2高星项目
- **ros-navigation/navigation2**: 模块化包结构典范
- **AREIVAN/ROS-2-Autonomous-Warehouse-Robot**: 功能分层设计
- **henki-robotics/henki_ros2_best_practices**: 命名和架构规范

### 官方文档
- ROS2官方工作空间教程
- Colcon构建系统文档
- ROS2包创建指南

---

**最后更新**: 2026-08-23  
**文档状态**: 待执行  
**预计完成时间**: 2-3天（分阶段实施）
