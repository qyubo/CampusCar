# CampusCar 项目总结文档

> 时间：2026-08-06  
> 项目状态：**开发中** - STM32 PWM 控制已打通，等待 NUC 串口联调

---
## 注意事项

1. 8月6日测试出现短路情况⚠️，电调金属外壳、降压模块金属外壳、分电板底部焊点需处理（如贴泡棉胶带）（已解决）

2. 连ssh需注意：NUC未知原因连不上校园网，目前连的网络是HKUST-GUEST（已解决）

3. 8月6日电池充电，下一个去MDMF的记得收回充电器

4. NUC 上的 `scripts/test_hoverboard_uart.py` 协议校验仍为旧版（加法校验），需重新下载更新为 XOR 校验版本（当前电脑端代码已更新为 XOR：`checksum = 0xABCD ^ steer ^ speed`，qyb回去后会更新）

5. 需要车动可先用遥控器，接线方式为：绿-CH1信号 蓝-CH2信号 红-CH1+ 黄-CH1-
信号初始化需要遥控器摇杆上下左右快速移动，听到音效即代表成功，接stm32同样需要此方式初始化（目前直接写进代码无法初始化，后续调整）

6. 需要什么直接买，开票给Jason，据学姐说会直接转钱不用报销流程（未知真假）

## 注意安全！⚠️

## 一、全流程路径架构

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            UE (客户端/远程控制)                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  UE 客户端 (Unity/Unreal)                                                │    │
│  │  • 发送指令 → /U2RTopic_Command                                         │    │
│  │  • 接收坐标 ← /R2UTopic_Pos                                             │    │
│  │  • 接收文本 ← /R2UTopic_Text                                            │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                              │                                                   │
│                              │ WebSocket (rosbridge)                              │
│                              ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  rosbridge_server (端口 9090)                                           │    │
│  │  • 提供 WebSocket 接口                                                  │    │
│  │  • 桥接 UE ↔ ROS2 话题                                                 │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                              │
                              │ ROS2 DDS
                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            NUC (Intel NUC)                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ROS2 Humble 中间件                                                     │    │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │    │
│  │  │ UE Bridge    │  │ Camera Server │  │ RTK Driver   │  │ Car GUI     │ │    │
│  │  │ (ue_bridge)  │  │ (MJPEG/RTSP) │  │ (rtk_tools)  │  │ (car_gui)   │ │    │
│  │  └─────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │    │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │    │
│  │  │               Hoverboard Driver (ROS2 Control)                       │ │    │
│  │  │  • 订阅 /cmd_vel → 转换为 PWM 命令 → 发送到 STM32                   │ │    │
│  │  │  • 读取 STM32 反馈 → 发布 /odom, /imu                              │ │    │
│  │  └─────────────────────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                              │                                                   │
│                              │ UART (115200, 8N1)                                │
│                              ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  USB-TTL 转换器 (CH340)                                                │    │
│  │  • NUC USB → GND, TXD → PA9, RXD → PA10 → STM32 USART1                │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                              │                                                   │
│                              │ PWM (50Hz, 1.0-2.0ms)                            │
│                              ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  STM32H723VGT6 (达妙 DM-MC02 开发板)                                   │    │
│  │  • TIM1_CH1 (PE9) → 电调 CH2 (速度)                                    │    │
│  │  • TIM1_CH3 (PE13) → 电调 CH1 (转向)                                   │    │
│  │  • USART1 (PA9/PA10) ← NUC 串口                                        │    │
│  │  • PC13 (STATUS_LED) - 状态指示                                        │    │
│  │  • PC14 (RUN_LED) - 运行指示                                           │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                              │                                                   │
│                              │ PWM 信号                                          │
│                              ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  电调 (ESC) + 电机                                                      │    │
│  │  • 接收 PWM 信号 (1.0ms=后退最大, 1.5ms=停止, 2.0ms=前进最大)          │    │
│  │  • 驱动 4 个电机                                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                              │                                                   │
│                              ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  4WD 底盘 (小车)                                                        │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 数据流路径

```
1. 本地控制路径 (Car GUI / Keyboard)
┌──────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────┐
│  Car GUI     │──▶│  /cmd_vel  │──▶│ Hoverboard │──▶│   STM32    │──▶│ 电调   │
│  键盘控制    │   │  ROS2 话题 │   │  Driver    │   │            │   │        │
└──────────────┘   └────────────┘   └────────────┘   └────────────┘   └────────┘
                                                                          │
                                                                          ▼
                                                                   ┌────────────┐
                                                                   │  4WD 底盘  │
                                                                   └────────────┘
```

```
2. UE 远程控制路径
┌────────┐   ┌────────────┐   ┌──────────────┐   ┌────────────┐   ┌────────┐
│   UE   │──▶│ rosbridge  │──▶│  /U2RTopic_  │──▶│  ue_bridge │──▶│ /cmd_vel│
│ 客户端 │   │  WebSocket │   │  Command     │   │  命令解析  │   │  ROS2  │
└────────┘   └────────────┘   └──────────────┘   └────────────┘   └────────┘
                                                                          │
                                                                          ▼
                                                                   ┌────────────┐
                                                                   │  Hoverboard│
                                                                   │  Driver    │
                                                                   └────────────┘
                                                                          │
                                                                          ▼ UART
                                                                   ┌────────────┐
                                                                   │   STM32    │
                                                                   └────────────┘
                                                                          │
                                                                          ▼ PWM
                                                                   ┌────────────┐
                                                                   │   电调     │
                                                                   └────────────┘
                                                                          │
                                                                          ▼
                                                                   ┌────────────┐
                                                                   │  4WD 底盘  │
                                                                   └────────────┘
```

---

## 二、已实现功能清单（诚实版）

### 2.1 STM32 固件 ✅ 已完成并测试

| 模块 | 功能 | 验证状态 |
|------|------|----------|
| **时钟配置** | HSE + PLL, 200MHz | ✅ 已烧录运行 |
| **GPIO** | PC13 (闪4次), PC14 (闪烁) | ✅ LED 实际闪烁 |
| **TIM1 PWM** | PE9 (CH1), PE13 (CH3) | ✅ 示波器验证 50Hz |
| **USART1** | PA9 (TX), PA10 (RX), 115200 | ✅ 串口收发正常 |
| **Hoverboard 协议** | 小端序, XOR 校验 | ✅ 电脑串口测试通过 |
| **命令处理** | steer/speed → PWM 映射 | ✅ 车轮实际移动 |
| **初始化序列** | 电调初始化（前后左右快速扳动）| ✅ 电调初始化成功 |
| **安全保护** | 1s 超时回到停止 | ✅ 代码已实现 |

### 2.2 NUC 端 ROS2 软件

| 模块 | 功能 | 代码状态 | 测试状态 |
|------|------|----------|----------|
| **rosbridge_server** | WebSocket 接口 (端口 9090) | ✅ 代码完成 | ⚠️ ROS2 话题级测试通过，未接 UE |
| **Hoverboard Driver** | ROS2 Control 底盘驱动 | ✅ 代码完成 | ❌ 未与 STM32 联调 |
| **UE Bridge** | UE 数据桥接 | ✅ 代码完成 | ⚠️ 话题级测试，未接真实 UE |
| **Car GUI** | 桌面控制界面 | ✅ 代码完成 | ❌ 未启动测试 |
| **Keyboard Control** | 终端键盘控制 | ✅ 代码完成 | ❌ 未启动测试 |
| **MJPEG Server** | 视频流 (端口 8080) | ✅ 代码完成 | ❌ 未连接相机 |
| **RTSP Server** | RTSP 推流 (端口 8554) | ✅ 代码完成 | ❌ 未连接相机 |
| **Hikrobot 相机驱动** | MV-CS016-10GC | ✅ 脚本完成 | ❌ 未连接 |
| **RTK GPS 模块** | 路径录制 + 航点导航 | ✅ 代码完成 | ❌ 未连接 |

### 2.3 仿真环境开发（小电脑端）

| 模块 | 功能 | 代码状态 | 测试状态 |
|------|------|----------|----------|
| **多传感器融合仿真** | 仿真环境跑多传感器融合 | ✅ 代码完成 | ⚠️ 正在调试中 |
| **RTK GPS 节点** | RTK 作为 ROS2 节点发送数据 | ✅ 代码完成 | ⚠️ 仿真虚拟数据已跑通 |
| **相机虚拟数据** | 相机节点用虚拟数据替代 | ✅ 代码完成 | ⚠️ 未接线，暂无真实数据 |
| **雷达虚拟数据** | 雷达节点用虚拟数据替代 | ✅ 代码完成 | ⚠️ 未接线，暂无真实数据 |
| **Gazebo Bridge** | Gazebo 与 ROS2 桥接 | ✅ 代码完成 | ❌ 存在格式和内存问题，待修复 |
| **UE5 集成** | 校园大脑替换为 UE5 | ❌ 待开发 | - |

### 2.4 实际测试验证总结

| 测试项 | 测试方式 | 结果 | 日期 |
|--------|----------|------|------|
| STM32 PWM 输出 | 示波器测 PE9/PE13 | 50Hz, 1.0-2.0ms 脉宽 ✅ | 2026-08-06 |
| 电调响应 PWM | 接电调 + 电机 | 车轮跟随 PWM 信号 ✅ | 2026-08-06 |
| 电脑串口控制 | 串口调试助手发送命令 | 车轮正确响应 ✅ | 2026-08-06 |
| Hoverboard 协议 | 小端序 + XOR 校验 | 协议解析正确 ✅ | 2026-08-06 |
| ROS2 话题发布 | `ros2 topic echo /cmd_vel` | 话题数据正确 ✅ | 2026-07-27 |
| /U2RTopic_Command | `ros2 topic pub` | 命令发布成功 ✅ | 2026-07-27 |
| NUC 识别 USB-TTL | `ls /dev/ttyUSB*` | 已成功 | - |
| NUC → STM32 串口 | NUC 直接控制 STM32 | ❌ 未测试 | - |
| 全栈联调 | UE → NUC → STM32 → 车轮 | ❌ 未测试 | - |
| 多传感器融合仿真 | 小电脑仿真环境 | ⚠️ 正在调试 | 2026-08-14 |
| RTK 节点数据发送 | 仿真环境 | ✅ 虚拟数据已跑通 | 2026-08-14 |
| Gazebo Bridge | Gazebo-ROS2 桥接 | ❌ 格式和内存问题待修复 | - |

### 2.5 硬件接入状态

| 模块 | 硬件状态 | 说明 |
|------|----------|------|
| **相机 (Hikrobot MV-CS016-10GC)** | ❌ 未接线 | 仿真用虚拟数据，接线后可切换真实数据 |
| **RTK GPS** | ❌ 未接线 | 仿真用虚拟数据，节点已跑通 |
| **雷达 (LiDAR)** | ❌ 未接线 | 仿真用虚拟数据，硬件已确认存在 |
| **STM32 底盘** | ⚠️ 待联调 | 代码已验证，等 NUC USB-TTL 识别后联调 |

### 2.6 待解决问题

| 问题 | 状态 | 影响 |
|------|------|------|
| **NUC USB-TTL 识别** | ❌ 未解决 | CH340 驱动已安装但设备未识别，阻碍 NUC→STM32 联调 |
| **SSH 连接 NUC** | ✅ 已配置并测试 | 可远程控制 NUC |
| **Gazebo Bridge 格式/内存问题** | ❌ 修复中 | 影响仿真环境稳定性 |
| **相机接线** | ❌ 未完成 | 无法获取真实视频流数据 |
| **RTK 接线** | ❌ 未完成 | 无法获取真实 GPS 数据 |
| **雷达接线** | ❌ 未完成 | 无法获取真实雷达点云数据 |
| **校园网连接** | ❌ 未解决 | NUC 无法连接校园网，临时使用 HKUST-GUEST |
| **NUC Python 脚本校验协议** | ❌ 需更新 | NUC 上 test_hoverboard_uart.py 校验仍为旧版，需同步为 XOR 版本 |

---

## 三、campusCar 项目架构

### 3.1 项目目录结构

```
campusCar-hardware-new-stm32-hikrobot/
├── config/                           # 配置文件
│   ├── robot.env                     # 主配置文件
│   └── profiles/
│       ├── stm32_hoverboard_4wd.env  # STM32 底盘配置
│       └── template.env              # 配置模板
│
├── hardware/                         # ROS2 硬件驱动
│   └── hoverboard_driver/            # Hoverboard 底盘驱动
│       ├── hardware/include/
│       │   ├── config.hpp            # 配置
│       │   ├── hoverboard_driver.hpp # 驱动头文件
│       │   ├── protocol.hpp          # Hoverboard 协议定义 ⭐
│       │   └── pid.hpp               # PID 控制器
│       ├── hardware/
│       │   ├── hoverboard_driver.cpp # 驱动实现
│       │   └── pid.cpp               # PID 实现
│       ├── bringup/
│       │   ├── config/hoverboard_controllers.yaml  # 控制器配置
│       │   └── launch/diffbot.launch.py # 启动文件
│       └── description/              # URDF/ros2_control 描述
│
├── scripts/                          # 启动/测试脚本
│   ├── launch_all.sh                 # 一键启动全栈
│   ├── stop_all.sh                   # 停止全栈
│   ├── check_all.sh                  # 状态检查
│   ├── stm32_hoverboard_start.sh     # 启动 STM32 驱动
│   ├── stm32_hoverboard_probe.sh     # 探测 STM32 设备
│   ├── hikrobot_camera_start.sh      # 启动相机
│   ├── hikrobot_camera_probe.sh      # 探测相机
│   ├── open_car_gui.sh               # 打开控制台
│   ├── keyboard_control.sh           # 启动键盘控制
│   └── test_hoverboard_uart.py       # UART 测试脚本
│
├── src/                              # Python 应用
│   ├── car_gui.py                    # 小车控制 GUI
│   ├── keyboard_control.py           # 终端键盘控制
│   ├── ue_bridge.py                  # UE 数据桥接
│   ├── mjpeg_server.py               # MJPEG 服务
│   ├── rtsp_server.py                # RTSP 服务
│   └── rtk_tools/                    # RTK/GPS 工具
│       ├── gps_navigator.py          # GPS 航点导航
│       ├── path_recorder.py          # 路径录制
│       ├── u2r_r2u_bridge.py         # UE 双向桥接
│       └── core/
│           ├── gnss.py               # GNSS 验证
│           └── bridge.py              # 桥接核心
│
├── docs/                             # 文档
│   ├── 快速启动指南.md
│   └── ...
│
└── docker/                           # Docker 配置
```

### 3.2 核心模块说明

#### Hoverboard Driver (ROS2 Control)

**文件位置**：`hardware/hoverboard_driver/`

**功能**：
- 实现 ROS2 Control 的 `SystemInterface`
- 通过 UART 与 STM32 通信
- 订阅 `/cmd_vel` → 转换为 PWM 命令 → 发送 STM32
- 读取 STM32 反馈 → 发布 `/odom`, `/imu`

**协议格式**（定义在 [protocol.hpp](file:///e:/CyberProject/CampusCar/campusCar-hardware-new-stm32-hikrobot/hardware/hoverboard_driver/hardware/include/hoverboard_driver/protocol.hpp)）：

```c
// 命令帧 (8 字节，小端序)
typedef struct {
   uint16_t start;     // 0xABCD
   int16_t  steer;     // [-1000, 1000]
   int16_t  speed;     // [-1000, 1000]
   uint16_t checksum;  // start ^ steer ^ speed
} SerialCommand;

// 反馈帧 (16 字节，小端序)
typedef struct {
   uint16_t start;
   int16_t  cmd1, cmd2;
   int16_t  speedR_meas, speedL_meas;  // 速度反馈
   int16_t  wheelR_cnt, wheelL_cnt;    // 编码器计数
   int16_t  left_dc_curr, right_dc_curr;
   int16_t  batVoltage, boardTemp;
   uint16_t cmdLed;
   uint16_t checksum;
} SerialFeedback;
```

#### Hikrobot 相机模块

**状态**：代码完成，未实际测试

- 型号：MV-CS016-10GC (GigE 网口相机)
- 驱动：基于 camera_aravis2
- 分辨率：1440×1080 @ 30fps
- 脚本：
  - `hikrobot_camera_probe.sh` - 探测相机
  - `hikrobot_camera_start.sh` - 启动相机

#### RTK GPS 模块

**状态**：代码完成，未实际测试

- 功能：
  - `gps_navigator.py` - GPS 航点导航（Stanley Controller）
  - `path_recorder.py` - 路径录制
  - `u2r_r2u_bridge.py` - UE 坐标桥接
- 控制算法：Stanley Controller
  ```
  δ = ψ_e + arctan(k * e / max(v, v_min))
  ```

### 3.3 启动流程

```
1. 环境准备
   source config/robot.env
   source ROS2 setup.bash

2. 一键启动 (launch_all.sh)
   ├─ rosbridge_server (端口 9090)
   ├─ hoverboard_driver (底盘驱动)
   ├─ camera_driver (相机驱动)  ← 若无相机则跳过
   ├─ rtsp_server (RTSP 推流)
   ├─ mjpeg_server (MJPEG 推流)
   ├─ ue_bridge (UE 桥接)
   └─ car_gui (控制界面)
```

---

## 四、ROS2 话题列表

### 4.1 已发布话题

| 话题 | 类型 | 说明 | 测试状态 |
|------|------|------|----------|
| `/cmd_vel` | geometry_msgs/Twist | 底盘控制指令 | ✅ 发布/订阅正常 |
| `/odom` | nav_msgs/Odometry | 里程计反馈 | ✅ 订阅数据正常 |
| `/fix` | sensor_msgs/NavSatFix | GPS 定位 | ⚠️ 话题存在，无真实数据 |
| `/heading` | std_msgs/Float32 | 航向角 | ⚠️ 话题存在 |
| `/U2RTopic_Command` | std_msgs/String | UE 指令入口 | ✅ 发布测试通过 |
| `/R2UTopic_Pos` | std_msgs/String | UE 坐标 (JSON) | ⚠️ 话题存在 |
| `/R2UTopic_Text` | std_msgs/String | UE 文本回复 | ⚠️ 话题存在 |
| `/rosout` | 内部话题 | 日志 | ✅ 正常 |
| `/parameter_events` | 内部话题 | 参数变化 | ✅ 正常 |

### 4.2 图片中的测试内容

**图片 1**：刚启动 ROS2 时，仅显示 `/rosout` 和 `/parameter_events`

**图片 2**：启动更多节点后，显示完整话题列表：
- `/U2RTopic_Text`, `/U2RTopic_Command`, `/cmd_vel`, `/connected_clients`
- `/fix`, `/heading`, `/odom`, `/R2UTopic_Pos`

**图片 3**：话题通信测试：
```bash
# 发布 UE 命令
ros2 topic pub --once /U2RTopic_Command std_msgs/msg/String \
  "{data: '{\"commandId\":\"010\",\"commandType\":\"Forward\",\"speed\":\"30\"}'}"

# 订阅 cmd_vel 反馈
ros2 topic echo /cmd_vel
# 结果: linear.x=0.3, angular.z=0.0 ✅
```

---

## 五、硬件连接图

### 5.1 接线图

```
┌──────────────┐     USB-TTL      ┌──────────────┐    UART    ┌──────────────┐
│    电脑       │ ──────────────→  │     NUC      │ ─────────→ │  STM32H723   │
│              │    GND → GND      │              │  115200   │  PA9 (TX)   │
│              │    RXD → PA9      │              │  8N1      │  PA10 (RX)  │
│              │    TXD → PA10     │              │           │  GND        │
└──────────────┘                   └──────────────┘           └──────────────┘
                                                                      │
                                                                      │ TIM1 PWM
                                                                      ▼
                                                               ┌──────────────┐
                                                               │     电调      │
                                                               │  CH2 ← PE9   │ (速度)
                                                               │  CH1 ← PE13  │ (转向)
                                                               │  GND ← GND  │
                                                               └──────────────┘
                                                                      │
                                                                      ▼
                                                               ┌──────────────┐
                                                               │  4WD 底盘    │
                                                               └──────────────┘
```

### 5.2 引脚分配

| 模块 | 引脚 | 功能 | 说明 |
|------|------|------|------|
| STM32 | PA9 | USART1_TX | TTL 串口发送 → NUC USB-TTL RXD |
| STM32 | PA10 | USART1_RX | TTL 串口接收 ← NUC USB-TTL TXD |
| STM32 | PE9 | TIM1_CH1 | PWM 输出 → 电调 CH2 (速度) |
| STM32 | PE13 | TIM1_CH3 | PWM 输出 → 电调 CH1 (转向) |
| STM32 | PC13 | STATUS_LED | 启动时闪 4 次 |
| STM32 | PC14 | RUN_LED | 主循环时闪烁 |
| STM32 | GND | 接地 | 必须与 NUC、电调共地 |

### 5.3 PWM 参数

```
时钟: HSE=25MHz → PLL×16/2 → SYSCLK=200MHz → TIM1=200MHz

参数:
  PSC=199    → 计数时钟 = 200MHz/200 = 1MHz
  Period=19999 → PWM频率 = 1MHz/20000 = 50Hz

脉宽:
  PWM_MIN   = 1000 → 1.0ms (后退最大)
  PWM_STOP  = 1500 → 1.5ms (停止)
  PWM_MAX   = 2000 → 2.0ms (前进最大)
```

---

## 六、下一步计划

### 优先级 1：解决 NUC 连接问题

```bash
# 1. 在 NUC 上检查 USB-TTL
ls /dev/ttyUSB*
# 如果没有
sudo modprobe ch341
ls /dev/ttyUSB*

# 2. 确认 SSH 服务
sudo systemctl status ssh
sudo systemctl start ssh

# 3. 从电脑测试 SSH
ssh qyb413@10.16.162.22
```

### 优先级 2：NUC → STM32 联调

```bash
# 1. 连接硬件（NUC USB → USB-TTL → STM32）
# 2. 确认串口设备
ls /dev/ttyUSB*

# 3. 运行测试脚本
python3 scripts/test_hoverboard_uart.py

# 4. 启动 ROS2 全栈
./scripts/launch_all.sh

# 5. 测试控制
./scripts/keyboard_control.sh
```

### 优先级 3：功能扩展

- 接入 Hikrobot 相机（若硬件就绪）
- 接入 RTK GPS（若硬件就绪）
- 对接 UE 远程控制

---

## 附录

### A. STM32 源码位置

- [main.c](file:///e:/CyberProject/CampusCar/CampusCar_STM32H723VGT6/Core/Src/main.c) - 主程序（PWM控制、协议解析、调试输出）
- [tim.c](file:///e:/CyberProject/CampusCar/CampusCar_STM32H723VGT6/Core/Src/tim.c) - TIM1 配置（50Hz PWM）
- [usart.c](file:///e:/CyberProject/CampusCar/CampusCar_STM32H723VGT6/Core/Src/usart.c) - USART1 配置（115200）
- [gpio.c](file:///e:/CyberProject/CampusCar/CampusCar_STM32H723VGT6/Core/Src/gpio.c) - GPIO 配置（LED）

### B. NUC 项目关键路径（已下载到 NUC）

**项目位置**：`~/CampusCar/`

**已下载的主要文件**：

```
~/CampusCar/
├── config/                           # ⭐ 配置文件
│   ├── robot.env                     # 主配置
│   └── profiles/stm32_hoverboard_4wd.env
│
├── hardware/                         # ⭐ ROS2 硬件驱动
│   └── hoverboard_driver/
│       ├── hardware/include/hoverboard_driver/protocol.hpp  # 协议定义
│       ├── hardware/hoverboard_driver.cpp
│       ├── bringup/config/hoverboard_controllers.yaml
│       └── bringup/launch/diffbot.launch.py
│
├── scripts/                          # ⭐ 启动/测试脚本
│   ├── launch_all.sh                 # 一键启动全栈
│   ├── stop_all.sh
│   ├── check_all.sh
│   ├── stm32_hoverboard_start.sh
│   ├── hikrobot_camera_start.sh
│   ├── open_car_gui.sh
│   ├── keyboard_control.sh
│   └── test_hoverboard_uart.py       # UART 测试脚本 ⭐
│
├── src/                              # ⭐ Python 应用
│   ├── car_gui.py                    # 控制 GUI
│   ├── keyboard_control.py
│   ├── ue_bridge.py
│   ├── mjpeg_server.py
│   ├── rtsp_server.py
│   └── rtk_tools/
│       ├── gps_navigator.py          # GPS 航点导航
│       ├── path_recorder.py          # 路径录制
│       └── u2r_r2u_bridge.py
│
└── docker/                           # Docker 配置
```



### C. 关键命令

```bash
# NUC 上操作
cd ~/CampusCar
./scripts/launch_all.sh          # 启动全栈
./scripts/keyboard_control.sh     # 键盘控制
python3 scripts/test_hoverboard_uart.py  # UART 测试

# ROS2 话题测试
ros2 topic list
ros2 topic echo /cmd_vel
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3}, angular: {z: 0.0}}"
```

---

**文档结束 - 最后更新 2026-08-06**
