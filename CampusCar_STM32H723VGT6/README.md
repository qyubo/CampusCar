# CampusCar STM32H723VGT6 固件

STM32H723VGT6 智能校园小车底盘控制固件，支持通过UART接收ROS2控制命令，控制电调驱动底盘电机和舵机转向。

## 项目简介

本项目是智能校园巡检小车的底盘控制固件，运行在STM32H723VGT6微控制器上。主要功能包括：

- **串口通信**：通过UART1接收NUC（上位机）发送的控制命令
- **电调控制**：通过UART7向Hoverboard电调发送速度和转向指令
- **舵机控制**：通过TIM2 PWM控制MG996R舵机实现精确转向
- **状态反馈**：定期向NUC发送底盘状态反馈
- **LED指示**：通过多个LED指示系统运行状态

### 主要特性

✅ 双UART通信架构（UART1接收命令 + UART7控制电调）  
✅ 50Hz PWM舵机控制（支持0-180°精确定位）  
✅ Hoverboard协议兼容（8字节命令帧 + 16字节反馈帧）  
✅ 完善的错误检查（帧头校验 + XOR校验和）  
✅ 超时保护机制（100ms无命令自动停车）  
✅ 模块化设计（舵机、电调、串口独立封装）

## 运行环境

### 硬件要求

| 组件 | 型号/规格 | 说明 |
|------|----------|------|
| MCU | STM32H723VGT6 | 主控芯片，ARM Cortex-M7 @550MHz |
| 电调 | Hoverboard电调 | 支持UART协议的无刷电调 |
| 舵机 | MG996R（或兼容型号） | 180°金属齿舵机 |
| 上位机 | NUC（运行ROS2） | 通过USB-UART连接 |
| 电源 | 12-24V电池 + 5V独立舵机电源 | - |

### 软件要求

| 软件 | 版本 | 用途 |
|------|------|------|
| STM32CubeMX | ≥6.0 | 外设配置和代码生成 |
| STM32CubeIDE | ≥1.10 或其他ARM工具链 | 编译和调试 |
| HAL库 | STM32H7xx HAL | 硬件抽象层 |
| 烧录工具 | ST-Link / J-Link | 固件下载 |

### 引脚分配

详见 [硬件连接说明](docs/hardware_connection.md)

关键引脚：
- **UART1**: PA9(TX), PA10(RX) - NUC通信
- **UART7**: PE7(RX), PE8(TX) - 电调通信  
- **TIM2_CH1**: PA0 - 舵机PWM
- **LED**: PC13, PC14, PC15

## 安装方式

### 1. 获取源码

```bash
git clone <your-repo-url>
cd CampusCar_STM32H723VGT6
```

### 2. 使用STM32CubeIDE编译

```bash
# 打开STM32CubeIDE
File → Open Projects from File System → 选择项目目录

# 编译
Project → Build All (Ctrl+B)
```

### 3. 使用命令行编译（CMake）

```bash
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../cmake/gcc-arm-none-eabi.cmake ..
make -j$(nproc)
```

生成的固件位于：`build/CampusCar_STM32H723VGT6.elf`

### 4. 烧录固件

#### 使用STM32CubeIDE
```
Run → Debug (F11)
或
Run → Run (Ctrl+F11)
```

#### 使用命令行（OpenOCD）
```bash
openocd -f interface/stlink.cfg -f target/stm32h7x.cfg \
  -c "program build/CampusCar_STM32H723VGT6.elf verify reset exit"
```

#### 使用ST-Link Utility
1. 打开ST-Link Utility
2. 连接目标板
3. File → Open File → 选择 .hex 或 .bin 文件
4. Target → Program & Verify

## 使用说明

### 快速启动

1. **硬件连接**
   - 按照 [硬件连接说明](docs/hardware_connection.md) 连接所有外设
   - 确保舵机使用独立5V电源供电
   - 检查所有GND共地

2. **上电测试**
   - 给STM32供电（USB或外部5V）
   - 观察PC13 LED快速闪烁4次（启动指示）
   - 舵机执行测试序列：0°→45°→90°→135°→180°→90°
   - PC14 LED持续500ms心跳闪烁

3. **连接NUC**
   - 将NUC通过USB-UART连接到STM32 UART1
   - 在NUC上配置串口：115200波特率，8N1
   - 启动ROS2驱动（见下文）

4. **测试控制**
   - 手动发送串口命令测试（见 [WASD测试指南](docs/wasd_test_guide.md)）
   - 或通过ROS2发布 `/cmd_vel` 话题

### 串口协议

#### 命令帧（NUC → STM32，8字节）

| Offset | 字段 | 类型 | 说明 |
|--------|------|------|------|
| 0-1 | start | uint16 | 帧头 0xABCD（小端序） |
| 2-3 | steer | int16 | 转向量 -1000~1000 |
| 4-5 | speed | int16 | 速度量 -1000~1000 |
| 6-7 | checksum | uint16 | XOR校验（start ^ steer ^ speed） |

#### 反馈帧（STM32 → NUC，16字节）

每200ms发送一次，详见代码中 `SerialFeedbackCompact` 结构体定义。

### 与ROS2集成

在NUC端启动Hoverboard驱动：

```bash
# 配置串口设备
export STM32_UART_DEVICE=/dev/ttyUSB0

# 启动驱动
ros2 run hoverboard_driver hoverboard_driver_node

# 发送控制命令
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5}, angular: {z: 0.0}}"
```

详细测试步骤见 [WASD测试指南](docs/wasd_test_guide.md)

### 调试信息

连接串口（115200波特率）可查看调试输出：

```
[SERVO] Init MG996R servo on TIM2_CH1 (PA00)...
[SERVO] Init OK, starting test sequence...
[STAGE] === 1 ===
[RX] AB CD 00 00 E8 03 25 CE
[OK] steer=0 speed=1000
[SERVO] Angle: 30°
```

## 项目结构

```
CampusCar_STM32H723VGT6/
├── Core/
│   ├── Inc/                          # 头文件
│   │   ├── main.h
│   │   ├── servo_controller.h        # 舵机控制模块
│   │   ├── hoverboard_usart_controller.h  # 电调UART控制
│   │   ├── esc_pwm_controller.h      # PWM电调控制（备用）
│   │   ├── tim.h                     # 定时器配置
│   │   ├── usart.h                   # UART配置
│   │   └── gpio.h                    # GPIO配置
│   └── Src/                          # 源文件
│       ├── main.c                    # 主程序
│       ├── servo_controller.c        # 舵机控制实现
│       ├── hoverboard_usart_controller.c
│       ├── hoverboard_usart_app_example.c
│       ├── esc_pwm_controller.c
│       ├── tim.c
│       ├── usart.c
│       ├── gpio.c
│       └── stm32h7xx_it.c            # 中断处理
├── Drivers/                          # STM32 HAL库
├── docs/                             # 文档目录
│   ├── wasd_test_guide.md           # WASD测试指南
│   ├── gpio_fix_summary.md          # GPIO修复说明
│   └── hardware_connection.md       # 硬件连接说明
├── CMakeLists.txt                    # CMake构建配置
├── CampusCar_STM32H723VGT6.ioc      # CubeMX配置文件
└── README.md                         # 本文件
```

## 常见问题

### 1. 舵机不动

**原因**：PA0未配置为TIM2_CH1复用功能

**解决**：已在 `tim.c` 的 `HAL_TIM_PWM_MspInit()` 中添加GPIO配置，详见 [GPIO修复说明](docs/gpio_fix_summary.md)

### 2. 串口无输出

**原因**：UART1连接错误或波特率不匹配

**解决**：
- 检查PA9(TX)、PA10(RX)接线
- 确认波特率115200
- 尝试交换TX/RX线

### 3. 小车不动但串口有数据

**原因**：UART7到电调连接问题

**解决**：
- 检查PE7(RX)、PE8(TX)到电调的接线
- 检查电调供电
- 用示波器测量UART7输出

### 4. ROS2驱动显示offline

**原因**：STM32未发送反馈帧

**解决**：
- 确认串口设备路径正确
- 检查STM32是否每200ms发送反馈帧
- 查看ROS2日志：`ros2 run ... --ros-args --log-level debug`

更多问题见 [WASD测试指南 - 故障排查](docs/wasd_test_guide.md#故障排查)

## 开发说明

### 修改CubeMX配置

1. 打开 `CampusCar_STM32H723VGT6.ioc`
2. 修改外设配置
3. 保存并生成代码（保留用户代码区）
4. 重新编译

**注意**：用户代码应放在 `USER CODE BEGIN/END` 注释块内，以防被覆盖。

### 添加新功能

模块化开发建议：
1. 在 `Core/Inc/` 创建头文件
2. 在 `Core/Src/` 创建实现文件
3. 在 `main.c` 的用户代码区调用
4. 更新 CMakeLists.txt（如果使用CMake）

## 版本历史

### v1.1.0 (2026-08-22)
- 🔧 修复：添加TIM2 GPIO配置，解决舵机不动问题
- 📝 文档：完善README和硬件连接说明
- 🗂️ 重构：文档整理到 `docs/` 目录

### v1.0.0 (2026-08-21)
- ✨ 初始版本
- ✅ 支持Hoverboard协议通信
- ✅ 舵机PWM控制
- ✅ 电调UART控制
- ✅ 状态反馈机制

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

本项目包含ST官方HAL库，遵循ST的许可协议。
用户代码部分根据项目需求确定许可证。

## 联系方式

如有问题，请通过以下方式联系：
- 提交GitHub Issue
- 项目维护者：[your-email]

---

**相关文档**：
- [WASD测试指南](docs/wasd_test_guide.md)
- [硬件连接说明](docs/hardware_connection.md)
- [GPIO修复说明](docs/gpio_fix_summary.md)
