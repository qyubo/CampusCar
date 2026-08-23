# WASD底盘控制测试指南

## ✅ 当前代码状态（已回滚）

### 协议配置
- **命令帧大小**: 8字节（标准hoverboard协议）
- **帧结构**:
  ```
  Offset | 字段      | 类型   | 说明
  -------|----------|--------|------------------
  0-1    | start    | uint16 | 0xABCD (小端)
  2-3    | steer    | int16  | -1000~1000 (转向)
  4-5    | speed    | int16  | -1000~1000 (速度)
  6-7    | checksum | uint16 | XOR校验
  ```

### 控制链路
```
UE5键盘(WASD) 
    ↓ 发布 /cmd_vel
ROS2节点
    ↓ hoverboard_driver转换
UART1 (NUC → STM32, 115200波特率)
    ↓ 8字节命令帧
STM32 parse_command()
    ↓ 解析并校验
HoverboardApp_SetCommand(steer, speed)
    ↓ 
UART7 (STM32 → 电调, 115200波特率)
    ↓ 26字节协议
电调
    ↓
底盘电机
```

---

## 🔧 测试前准备

### 1. 硬件连接检查
- [ ] STM32 UART1 (PA9/PA10) ↔ NUC USB串口转换器
- [ ] STM32 UART7 (PE7/PE8) ↔ 电调 USART2 (PA2/PA3)
- [ ] 舵机信号线 (橙/黄) → PA0 (TIM2_CH1)
- [ ] 舵机电源 (红) → 独立5V电源
- [ ] 舵机地线 (棕/黑) → GND (与STM32共地)
- [ ] 电调供电正常（电池已连接）

### 2. 编译并烧录STM32固件
```bash
cd CampusCar_STM32H723VGT6
# 使用你的编译工具链编译并烧录
```

### 3. 确认NUC端ROS2驱动配置
检查 `campusCar-hardware-new-stm32-hikrobot/config/robot.env`:
```bash
# 串口设备（根据实际情况修改）
STM32_UART_DEVICE=/dev/ttyUSB0  # 或 /dev/ttyACM0

# 波特率
BAUD_RATE=115200
```

---

## 🚀 测试步骤

### 步骤1: 验证STM32独立运行

**上电后观察：**
1. **PC13 LED** 快速闪烁4次（启动指示）
2. **舵机动作**:
   - 执行测试序列：0°→45°→90°→135°→180°→90°
   - 进入主循环后持续扫描：20°↔160°（每500ms移动10°）
3. **PC14 LED** 持续500ms心跳闪烁
4. **串口输出**（连接UART1查看，115200波特率）:
   ```
   [SERVO] Init MG996R servo...
   [SERVO] Init OK...
   [STAGE] === 1 ===
   ...
   [SERVO] Angle: 20°
   [SERVO] Angle: 30°
   ...
   ```

**如果上述都正常，说明STM32固件工作正常。**

---

### 步骤2: 测试串口通信（不连ROS2）

在NUC上使用串口调试工具手动发送命令：

```bash
# 安装工具
sudo apt install python3-serial

# 测试脚本
python3 << 'EOF'
import serial
import struct
import time

# 打开串口
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(0.5)

def send_command(steer, speed):
    """发送8字节命令"""
    start = 0xABCD
    checksum = start ^ (steer & 0xFFFF) ^ (speed & 0xFFFF)
    data = struct.pack('<Hhhh', start, steer, speed, checksum)
    ser.write(data)
    print(f"发送: steer={steer}, speed={speed}")
    
    # 等待反馈帧（16字节）
    time.sleep(0.05)
    if ser.in_waiting >= 16:
        feedback = ser.read(16)
        print(f"收到反馈: {feedback.hex()}")

# 测试1: 前进
print("\n测试1: 前进 (speed=500)")
send_command(steer=0, speed=500)
time.sleep(2)

# 测试2: 后退
print("\n测试2: 后退 (speed=-500)")
send_command(steer=0, speed=-500)
time.sleep(2)

# 测试3: 左转
print("\n测试3: 左转 (steer=500)")
send_command(steer=500, speed=0)
time.sleep(2)

# 测试4: 右转
print("\n测试4: 右转 (steer=-500)")
send_command(steer=-500, speed=0)
time.sleep(2)

# 测试5: 停止
print("\n测试5: 停止")
send_command(steer=0, speed=0)

ser.close()
EOF
```

**预期结果：**
- 小车按指令运动
- STM32串口打印接收到的命令
- PC13闪烁表示收到有效命令

---

### 步骤3: 测试ROS2控制

#### 3.1 启动ROS2驱动
```bash
cd campusCar-hardware-new-stm32-hikrobot
./scripts/hoverboard_driver_start.sh
```

**检查驱动状态：**
```bash
# 查看话题
ros2 topic list | grep cmd_vel
# 应该看到: /cmd_vel

# 查看驱动状态
ros2 topic echo /hoverboard_driver/status
# 应该显示: connected: true
```

#### 3.2 手动发送ROS2命令测试
```bash
# 测试前进
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# 测试后退
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: -0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# 测试左转
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 1.0}}"

# 测试右转
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -1.0}}"

# 停止
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

---

### 步骤4: 测试UE5键盘控制

#### 4.1 启动UE5校园大脑
```bash
# 启动UE5项目（具体命令根据你的项目配置）
```

#### 4.2 检查ROS2桥接
确保UE5已经连接到ROS2，能够发布 `/cmd_vel` 话题。

#### 4.3 按键测试
- **W键** - 前进
- **S键** - 后退
- **A键** - 左转
- **D键** - 右转
- **松开** - 停止

---

## 🐛 故障排查

### 问题1: 串口打印无输出
**原因：** UART1连接错误或波特率不匹配
**解决：**
- 检查PA9(TX)、PA10(RX)接线
- 确认串口工具波特率115200
- 尝试交换TX/RX线

### 问题2: 小车不动但串口有数据
**原因：** UART7到电调的连接问题
**解决：**
- 检查PE7(RX)、PE8(TX)到电调的接线
- 用示波器测量UART7输出波形
- 检查电调供电

### 问题3: 舵机不动
**原因：** 5V供电不足或信号线断开
**解决：**
- 测量舵机5V引脚电压（应≥4.8V）
- 检查PA0信号线连接
- 用示波器测PA0波形（50Hz，脉宽0.5~2.5ms）

### 问题4: ROS2驱动显示offline
**原因：** STM32未发送反馈帧或串口未连接
**解决：**
- 确认串口设备路径正确（/dev/ttyUSB0）
- 检查STM32是否每200ms发送反馈帧
- 查看ROS2日志：`ros2 run hoverboard_driver hoverboard_driver --ros-args --log-level debug`

### 问题5: 收到命令但解析失败
**原因：** 协议不匹配或字节序错误
**解决：**
- 确认NUC端和STM32都是8字节协议
- 检查校验和计算（XOR所有字段）
- 查看STM32串口打印的原始数据

---

## 📊 调试信息收集

如果遇到问题，请提供以下信息：

1. **STM32串口输出日志**（连接UART1查看）
2. **LED闪烁模式**（PC13和PC14的行为）
3. **舵机是否正常扫描**
4. **ROS2驱动日志**：
   ```bash
   ros2 topic echo /hoverboard_driver/status
   ```
5. **手动串口测试结果**（步骤2的输出）

---

## 🎯 下一步计划

✅ **当前阶段：** 确保WASD底盘控制正常工作
⏳ **下个阶段：** 添加视觉反馈舵机控制
   - 扩展协议为10字节（增加servo_angle字段）
   - 创建视觉节点处理相机画面
   - 根据目标位置自动调整舵机角度

---

## 📝 修改记录

### 2026-08-21 回滚
- ✅ 协议从10字节回滚为8字节（移除servo_angle）
- ✅ 舵机保持独立测试模式（持续扫描20°~160°）
- ✅ 确保与NUC端ROS2驱动协议兼容
- ✅ 主循环恢复舵机测试代码

### 之前修改
- TIM2预分频器修正为191（匹配192MHz时钟）
- 添加舵机控制模块（servo_controller.c/h）
- 串口接收改为非阻塞（超时1ms）
