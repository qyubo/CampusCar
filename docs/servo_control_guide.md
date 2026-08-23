# 舵机三档位控制说明

## 硬件连接
- **舵机型号**: MG996R
- **连接**: STM32H723VGT6 的 TIM2_CH1（PWM）+ 5V + GND
- **工作范围**: 0-180度
- **PWM规格**: 
  - 90度（中位）: 1.5ms
  - 0度: 0.5ms  
  - 180度: 2.5ms

## 三档位设置
- **档位1**: 90度（中位，相机水平）
- **档位2**: 60度（向连线方向转30度，**可能需要改成120度**）
- **档位3**: 120度（另一方向转30度，**可能需要改成60度**）

> ⚠️ 档位2和档位3的角度需要现场测试确定正确方向

## NUC端代码架构

### 1. 文件结构
```
nuc/robot/ros2_workspace_src/
├── src/cri_drivers/chassis_driver/chassis_driver/
│   ├── servo_keyboard_control.py    # 键盘监听节点
│   ├── servo_uart_driver.py         # 串口驱动节点
│   └── setup.py                     # 已更新入口点
└── scripts/
    ├── servo_test.py                # 独立测试脚本
    └── servo_control_start.py       # 启动脚本
```

### 2. 通信协议

#### ROS2话题
```
/servo_command (std_msgs/UInt8)
  - 发布者: servo_keyboard_control
  - 订阅者: servo_uart_driver
  - 数据: 舵机角度 0-180
```

#### 串口协议（NUC → STM32）
```
帧格式（8字节）:
[0xAA, 0xBB, angle, 0x00, 0x00, 0x00, 0x00, checksum]

- 帧头: 0xAA 0xBB
- angle: 舵机角度 0-180 (uint8)
- 保留字节: 0x00 x 4
- checksum: (0xAA + 0xBB + angle) & 0xFF
```

示例：
- 90度: `AA BB 5A 00 00 00 00 1F`
- 60度: `AA BB 3C 00 00 00 00 01`
- 120度: `AA BB 78 00 00 00 00 3D`

### 3. 流程图
```
┌─────────────┐      /servo_command      ┌──────────────┐
│  键盘监听    │ ────────(UInt8)────────> │  串口驱动     │
│  节点        │      (角度 0-180)        │  节点         │
│             │                          │              │
│ 监听1/2/3/q │                          │ 构建协议帧    │
└─────────────┘                          └──────┬───────┘
                                                │
                                         串口 /dev/ttyUSB0
                                         115200 baud
                                                │
                                                ↓
                                         ┌──────────────┐
                                         │   STM32      │
                                         │  TIM2_CH1    │
                                         │   PWM输出    │
                                         └──────┬───────┘
                                                │
                                                ↓
                                         ┌──────────────┐
                                         │   MG996R     │
                                         │   舵机       │
                                         └──────────────┘
```

## 使用步骤

### 步骤1: 编译ROS2包
```bash
cd /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src
source /opt/ros/humble/setup.bash
colcon build --packages-select chassis_driver
source install/setup.bash
```

### 步骤2: 测试舵机连接（可选）
使用独立测试脚本快速验证串口和舵机响应：

```bash
cd /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts
chmod +x servo_test.py
python3 servo_test.py --port /dev/ttyUSB0

# 然后按键测试：
# 1 - 90度
# 2 - 60度  <-- 观察舵机转向
# 3 - 120度 <-- 观察舵机转向
# a - 自定义角度
# q - 退出
```

**通过此测试确定档位2应该是60度还是120度**

### 步骤3: 启动完整系统
```bash
cd /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts
chmod +x servo_control_start.py
python3 servo_control_start.py
```

或者分别启动两个节点：

**终端1 - 串口驱动：**
```bash
source /opt/ros/humble/setup.bash
source /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/install/setup.bash
ros2 run chassis_driver servo_uart_driver \
  --ros-args \
  -p serial_port:=/dev/ttyUSB0 \
  -p baud_rate:=115200
```

**终端2 - 键盘控制：**
```bash
source /opt/ros/humble/setup.bash
source /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/install/setup.bash
ros2 run chassis_driver servo_keyboard_control \
  --ros-args \
  -p gear1_angle:=90 \
  -p gear2_angle:=60 \
  -p gear3_angle:=120
```

### 步骤4: 键盘操作
启动后，在键盘控制节点的终端按键：
- **1** - 档位1（90度中位）
- **2** - 档位2（60度或120度）
- **3** - 档位3（120度或60度）
- **h** - 显示帮助
- **q** - 退出

## 调整档位角度

如果测试后发现档位2/3的方向不对，修改启动参数：

```bash
# 如果60度和120度方向反了，交换它们：
ros2 run chassis_driver servo_keyboard_control \
  --ros-args \
  -p gear1_angle:=90 \
  -p gear2_angle:=120 \  # 改成120
  -p gear3_angle:=60     # 改成60
```

或者修改 [servo_control_start.py](file:///home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/servo_control_start.py#L38-L40) 中的参数。

## STM32端需要的修改

STM32需要添加串口接收处理代码，识别舵机控制协议并输出PWM：

### 需要实现的功能
1. **串口接收**：监听 UART（与NUC通信的串口）
2. **协议解析**：识别 `0xAA 0xBB` 帧头，提取角度和校验
3. **PWM输出**：将角度转换为PWM脉宽
   ```c
   // MG996R: 0度=0.5ms, 90度=1.5ms, 180度=2.5ms
   // 假设TIM2频率50Hz，ARR=20000（20ms周期）
   // CCR = 500 + angle * 1000 / 90
   // 例如：90度 -> CCR = 500 + 90*11.11 = 1500
   ```
4. **TIM2_CH1配置**：50Hz PWM输出

### STM32示例伪代码
```c
// 在UART接收中断或DMA回调中
void process_servo_command(uint8_t *buffer, uint16_t len) {
    if (len >= 8 && buffer[0] == 0xAA && buffer[1] == 0xBB) {
        uint8_t angle = buffer[2];
        uint8_t checksum = buffer[7];
        
        // 校验
        if (checksum == ((0xAA + 0xBB + angle) & 0xFF)) {
            // 限制角度
            if (angle <= 180) {
                // 转换为PWM占空比
                // TIM2 50Hz, ARR=20000
                // 0.5ms -> CCR=500, 2.5ms -> CCR=2500
                uint16_t ccr = 500 + (angle * 2000 / 180);
                __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, ccr);
            }
        }
    }
}
```

## 常见问题

### Q: 串口找不到
```bash
# 查看可用串口
ls /dev/ttyUSB* /dev/ttyACM*

# 添加串口权限
sudo usermod -aG dialout $USER
# 然后重新登录
```

### Q: 舵机不动
1. 检查STM32是否正确接收串口数据
2. 检查TIM2_CH1是否输出PWM波形
3. 检查舵机供电是否正常（5V，电流足够）
4. 使用示波器测量PWM波形

### Q: 舵机抖动
1. 供电不足，使用外部5V电源
2. PWM频率不对，应为50Hz
3. 代码中频繁发送指令，添加防抖

## 下一步扩展
1. 添加平滑插值，避免舵机突然转动
2. 支持更多档位（4档、5档）
3. 添加角度反馈（如果使用数字舵机）
4. 集成到相机控制系统中
