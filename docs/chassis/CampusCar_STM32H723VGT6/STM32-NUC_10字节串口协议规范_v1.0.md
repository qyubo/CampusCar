# STM32与NUC 10字节串口通信协议

## 一、通信参数

- **串口**：UART1（STM32端：PA9 TX, PA10 RX）
- **波特率**：115200
- **数据位**：8
- **停止位**：1
- **校验位**：无
- **字节序**：小端序（Little-Endian）

---

## 二、命令帧格式（NUC → STM32，10字节）

### 帧结构

| 字节偏移 | 字段名 | 类型 | 字节数 | 取值范围 | 说明 |
|---------|--------|------|--------|----------|------|
| 0-1 | start | uint16_t | 2 | 0xABCD | 帧头（固定值） |
| 2-3 | steer | int16_t | 2 | -1000 ~ 1000 | 转向命令 |
| 4-5 | speed | int16_t | 2 | -1000 ~ 1000 | 速度命令 |
| 6 | servo_gear | uint8_t | 1 | 0/1/2/3 | 舵机档位 |
| 7 | reserved | uint8_t | 1 | 0 | 保留字段 |
| 8-9 | checksum | uint16_t | 2 | 计算值 | XOR校验和 |

### 字段详细说明

#### 1. start（帧头）
- **固定值**：`0xABCD`
- **小端序**：字节流为 `CD AB`

#### 2. steer（转向命令）
- **类型**：有符号16位整数
- **范围**：-1000 ~ 1000
- **说明**：
  - 正值：左转
  - 负值：右转
  - 0：直行

#### 3. speed（速度命令）
- **类型**：有符号16位整数
- **范围**：-1000 ~ 1000
- **说明**：
  - 正值：前进
  - 负值：后退
  - 0：停止

#### 4. servo_gear（舵机档位）
- **类型**：无符号8位整数
- **取值**：
  - `0`：不改变档位（保持当前状态）
  - `1`：档位1（60°）
  - `2`：档位2（90°，中位）
  - `3`：档位3（120°）
- **说明**：如果只想控制底盘不改变舵机，将此字段设为0

#### 5. reserved（保留字段）
- **类型**：无符号8位整数
- **当前值**：固定填 `0`
- **说明**：为未来扩展预留

#### 6. checksum（校验和）
- **类型**：无符号16位整数
- **计算方法**：
  ```
  checksum = start ^ steer ^ speed ^ (servo_gear | (reserved << 8))
  ```
- **说明**：所有字段按16位进行异或运算

---

## 三、校验和计算示例

### Python实现
```python
import struct

def calculate_checksum(start, steer, speed, servo_gear, reserved):
    """计算10字节协议的校验和"""
    checksum = start ^ (steer & 0xFFFF) ^ (speed & 0xFFFF) ^ ((servo_gear & 0xFF) | ((reserved & 0xFF) << 8))
    return checksum & 0xFFFF

# 示例：steer=0, speed=0, servo_gear=2（切换到档位2）
start = 0xABCD
steer = 0
speed = 0
servo_gear = 2
reserved = 0

checksum = calculate_checksum(start, steer, speed, servo_gear, reserved)
print(f"Checksum: 0x{checksum:04X}")  # 输出：0xABCF
```

### C语言实现
```c
uint16_t calculate_checksum(uint16_t start, int16_t steer, int16_t speed, uint8_t servo_gear, uint8_t reserved)
{
    uint16_t checksum = start ^ 
                        (uint16_t)steer ^ 
                        (uint16_t)speed ^ 
                        ((uint16_t)servo_gear | ((uint16_t)reserved << 8));
    return checksum;
}
```

---

## 四、完整数据包示例

### 示例1：控制底盘前进，切换舵机到档位2
```
steer = 0
speed = 500（前进，50%速度）
servo_gear = 2（90度）
```

**字节流（16进制）**：
```
CD AB    // start = 0xABCD（小端）
00 00    // steer = 0
F4 01    // speed = 500（小端：0x01F4）
02       // servo_gear = 2
00       // reserved = 0
CF AB    // checksum = 0xABCF（小端）
```

**Python打包代码**：
```python
import struct

def pack_command(steer, speed, servo_gear):
    start = 0xABCD
    reserved = 0
    
    # 计算校验和
    checksum = start ^ (steer & 0xFFFF) ^ (speed & 0xFFFF) ^ ((servo_gear & 0xFF) | 0)
    
    # 打包（小端序）
    data = struct.pack('<HhhBBH', 
        start,       # H: unsigned short (2 bytes)
        steer,       # h: signed short (2 bytes)
        speed,       # h: signed short (2 bytes)
        servo_gear,  # B: unsigned char (1 byte)
        reserved,    # B: unsigned char (1 byte)
        checksum     # H: unsigned short (2 bytes)
    )
    
    return data

# 示例使用
data = pack_command(0, 500, 2)
print("发送字节流:", data.hex(' '))
```

### 示例2：只控制底盘，不改变舵机
```
steer = -300（右转）
speed = 800（前进）
servo_gear = 0（不改变）
```

**Python代码**：
```python
data = pack_command(-300, 800, 0)
# servo_gear = 0 时舵机保持当前档位不变
```

### 示例3：只控制舵机，底盘停止
```
steer = 0
speed = 0
servo_gear = 1（切换到60度）
```

**Python代码**：
```python
data = pack_command(0, 0, 1)
# 底盘停止，舵机切换到档位1
```

---

## 五、反馈帧格式（STM32 → NUC，16字节）

STM32会周期性（每200ms）向NUC发送反馈帧，格式如下：

| 字节偏移 | 字段名 | 类型 | 字节数 | 说明 |
|---------|--------|------|--------|------|
| 0-1 | start | uint16_t | 2 | 帧头 0xABCD |
| 2-3 | cmd1 | int16_t | 2 | 回显steer命令 |
| 4-5 | cmd2 | int16_t | 2 | 回显speed命令 |
| 6-7 | speedR_meas | int16_t | 2 | 右轮转速（当前为0） |
| 8-9 | speedL_meas | int16_t | 2 | 左轮转速（当前为0） |
| 10-11 | batVoltage | int16_t | 2 | 电池电压×100（如2400=24.0V） |
| 12-13 | boardTemp | int16_t | 2 | 板温×10（如250=25.0°C） |
| 14-15 | cmdLed | uint16_t | 2 | LED命令（0） |
| 16-17 | checksum | uint16_t | 2 | XOR校验和 |

**注意**：反馈帧为16字节，与命令帧（10字节）不同！

---

## 六、通信时序

1. **NUC发送命令帧**（10字节）
2. **STM32接收并解析**
   - 检查帧头是否为0xABCD
   - 验证校验和
   - 执行底盘控制（steer/speed）
   - 执行舵机控制（servo_gear）
3. **STM32立即回复反馈帧**（16字节）
4. **STM32周期性发送反馈帧**（每200ms一次）

---

## 七、错误处理

### STM32端
- 帧头错误：丢弃数据包，打印 `[FAIL] Bad header`
- 校验错误：丢弃数据包，打印 `[FAIL] Bad checksum`
- 超过1秒未收到命令：底盘进入安全停止状态（舵机保持）

### NUC端建议
- 超过1秒未收到反馈帧：判定通信断开
- 发送命令后等待反馈帧确认
- 建议以50-100ms频率发送命令保持连接

---

## 八、调试串口输出

STM32通过UART1输出调试信息（115200波特率），格式如下：

```
[RX] CD AB 00 00 F4 01 02 00 CF AB      // 接收到的原始字节
[OK] steer=0 speed=500 servo_gear=2     // 解析成功
[SERVO] Gear 2 -> 90°                   // 舵机执行档位切换
```

---

## 九、完整Python测试代码

```python
#!/usr/bin/env python3
import serial
import struct
import time

class STM32Controller:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        
    def pack_command(self, steer, speed, servo_gear):
        """打包10字节命令帧"""
        start = 0xABCD
        reserved = 0
        
        # 限制范围
        steer = max(-1000, min(1000, steer))
        speed = max(-1000, min(1000, speed))
        servo_gear = max(0, min(3, servo_gear))
        
        # 计算校验和
        checksum = start ^ (steer & 0xFFFF) ^ (speed & 0xFFFF) ^ ((servo_gear & 0xFF) | 0)
        
        # 打包（小端序）
        data = struct.pack('<HhhBBH', 
            start, steer, speed, servo_gear, reserved, checksum
        )
        
        return data
    
    def send_command(self, steer=0, speed=0, servo_gear=0):
        """发送命令到STM32"""
        data = self.pack_command(steer, speed, servo_gear)
        self.ser.write(data)
        print(f"发送: steer={steer}, speed={speed}, servo_gear={servo_gear}")
        print(f"字节流: {data.hex(' ')}")
    
    def read_feedback(self):
        """读取反馈帧（16字节）"""
        if self.ser.in_waiting >= 16:
            data = self.ser.read(16)
            print(f"反馈帧: {data.hex(' ')}")
            return data
        return None

# 使用示例
if __name__ == '__main__':
    stm32 = STM32Controller('/dev/ttyUSB0')  # 根据实际串口修改
    
    # 测试舵机三档位
    print("\n测试档位1（60度）")
    stm32.send_command(steer=0, speed=0, servo_gear=1)
    time.sleep(2)
    
    print("\n测试档位2（90度）")
    stm32.send_command(steer=0, speed=0, servo_gear=2)
    time.sleep(2)
    
    print("\n测试档位3（120度）")
    stm32.send_command(steer=0, speed=0, servo_gear=3)
    time.sleep(2)
    
    # 测试底盘+舵机联动
    print("\n前进 + 档位2")
    stm32.send_command(steer=0, speed=500, servo_gear=2)
```

---

## 十、注意事项

1. **字节序**：所有多字节字段均为小端序
2. **类型转换**：计算校验和时需要将int16_t转换为uint16_t
3. **档位0**：servo_gear=0时舵机不动作，便于单独控制底盘
4. **反馈帧**：命令帧10字节，反馈帧16字节，不要混淆
5. **超时保护**：建议NUC端以≤1秒的周期持续发送命令

---

**文档版本**：1.0  
**更新日期**：2026-08-22  
**对应STM32固件版本**：commit 0531f1e
