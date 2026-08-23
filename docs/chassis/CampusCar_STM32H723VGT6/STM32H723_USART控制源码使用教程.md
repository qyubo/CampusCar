# STM32H723VGT6 USART控制源码使用教程

## 1. 文档和源码范围

本教程对应目录：

```text
STM32H723_USART_Controller/
├── Core/Inc/hoverboard_usart_controller.h
├── Core/Src/hoverboard_usart_controller.c
├── Application/hoverboard_usart_app_example.h
└── Application/hoverboard_usart_app_example.c
```

这套代码用于 STM32H723VGT6 作为上位机，通过 USART 控制当前驱动器固件。

源码只实现：

- 8字节运动控制帧 `0xABCD`。
- 8字节状态控制帧 `0xABCE`。
- 26字节反馈帧解析和 XOR 校验。
- RELEASE、RESUME、ESTOP、解除ESTOP。
- ACK序号、接受位和目标状态校验。

源码不包含：

- PWM输入。
- RC接收机。
- 电机FOC控制。
- STM32H723的具体时钟、启动文件和板级电源控制。

时钟、GPIO、UART实例和中断向量由 STM32CubeMX/CubeIDE 工程生成。

## 2. 硬件连接

### 2.1 驱动器一侧

当前驱动器固件使用 USART2：

| 驱动器信号 | STM32F103驱动器引脚 | 方向 |
|---|---|---|
| USART2_TX | PA2 | 驱动器发送反馈 |
| USART2_RX | PA3 | 驱动器接收控制 |
| GND | GND | 共地 |

### 2.2 H723控制器一侧

示例默认使用 H723 的 `USART1`，CubeMX可选择：

| H723示例 | 方向 | 连接 |
|---|---|---|
| USART1_TX | 控制器发送 | 接驱动器 PA3 / USART2_RX |
| USART1_RX | 控制器接收 | 接驱动器 PA2 / USART2_TX |
| GND | 共地 | 接驱动器 GND |

实际 H723 开发板的 USART1 引脚可能被板载功能占用。可以在 CubeMX 选择其他可用 UART，只要在应用代码中把 `huart1` 改成对应句柄即可。

### 2.3 电平和供电

- 驱动器 USART2 不是5 V容忍输入，控制器必须输出3.3 V TTL。
- H723和驱动器必须共地。
- 不要用驱动器接口的12/15 V给H723 GPIO或3.3 V电源脚供电。
- TX/RX必须交叉连接。
- 首次联调建议串入保险和准备独立断电手段。

## 3. 创建CubeMX工程

### 3.1 选择芯片

在 STM32CubeIDE 中：

1. `File -> New -> STM32 Project`。
2. 选择 MCU `STM32H723VGT6`。
3. 工程名例如 `H723_Hoverboard_USART`。
4. 选择 HAL 库和 C 工程。

### 3.2 配置UART

在 `Pinout & Configuration` 中配置一个异步UART。下面以 USART1 为例：

```text
Mode: Asynchronous
Baud Rate: 115200
Word Length: 8 Bits
Parity: None
Stop Bits: 1
Hardware Flow Control: None
Oversampling: 16
```

在 `NVIC Settings` 中勾选该 UART 的 global interrupt，例如 `USART1 global interrupt`。

本协议的串口参数必须与上述设置一致。驱动器当前也固定为 `115200 8N1`。

### 3.3 时钟

H723 的时钟树由具体开发板晶振和供电方案决定。使用 CubeMX 的 `Clock Configuration` 生成合法配置即可，不要直接复制其他 H7 板卡的时钟代码。

使用 HSE 时，应把外部晶振频率设置为开发板实际数值；使用 HSI 时，应确认系统时钟和Flash延迟由CubeMX正确生成。

## 4. 导入源码

将以下两个文件复制到CubeMX工程对应目录：

```text
hoverboard_usart_controller.h -> Core/Inc/
hoverboard_usart_controller.c -> Core/Src/
hoverboard_usart_app_example.h -> Application/ 或加入工程头文件路径
```

然后将：

```text
Application/hoverboard_usart_app_example.c
```

加入工程。该文件默认引用：

```c
extern UART_HandleTypeDef huart1;
```

如果CubeMX使用 USART2、USART3或其他 UART，则修改为对应的全局句柄。

确认工程包含：

```c
#include "hoverboard_usart_controller.h"
```

CubeMX生成的 `main.h` 必须能被 `hoverboard_usart_controller.h` 找到。

## 5. 在main中启动

在CubeMX生成的 `main.c` 中，按以下顺序调用：

```c
/* USER CODE BEGIN Includes */
#include "hoverboard_usart_app_example.h"
/* USER CODE END Includes */
```

在所有硬件初始化完成后调用：

```c
/* USER CODE BEGIN 2 */
HoverboardApp_Init();
/* USER CODE END 2 */
```

在主循环中调用：

```c
while (1)
{
  /* USER CODE END WHILE */

  /* USER CODE BEGIN 3 */
  HoverboardApp_20msTask();
  HAL_Delay(1);
  /* USER CODE END 3 */
}
```

`HoverboardApp_Init()`会启动1字节UART接收中断，并立即发送一帧零运动命令。`HoverboardApp_20msTask()`默认每20 ms发送一帧当前运动命令，满足驱动器约0.8秒的USART超时保护要求。

示例任务还会检查最近100 ms内是否收到合法反馈；反馈不新鲜时只发送零帧，不发送应用层保存的非零命令。

不要在同一个 UART 上使用 `printf` 输出调试信息，否则文本会被驱动器当成非法输入。调试信息应使用 SWV、USB CDC 或另一个UART。

## 6. 发布运动命令

应用层调用：

```c
extern void HoverboardApp_SetCommand(int16_t steer, int16_t speed);

/* 前进，约30%的串口命令幅值 */
HoverboardApp_SetCommand(0, 300);

/* 后退 */
HoverboardApp_SetCommand(0, -300);

/* 左转 */
HoverboardApp_SetCommand(-300, 0);

/* 右转 */
HoverboardApp_SetCommand(300, 0);

/* 停止 */
HoverboardApp_SetCommand(0, 0);
```

运动参数范围是 `-1000~1000`，超出范围时源码会自动限幅。

当前驱动器默认最大电机转速为500 rpm，但实际车辆速度仍受轮径、减速比、固件混控系数和电池电压影响。首次测试必须架空车轮，并从 `100~200` 的低命令开始。

## 7. RELEASE、RESUME和ESTOP

### 7.1 RELEASE

```c
HOVER_Result_t result = HoverboardApp_Release();
```

成功条件：

- 收到新的 `controlAck`。
- ACK命令号为 RELEASE。
- ACK接受位为1。
- `driverState == HOVER_STATE_RELEASE`。

RELEASE会让固件切换到 `VLT_MODE` 并强制零命令，接近自由滑行。它不是硬件急停，也不是主动制动。

### 7.2 RESUME

```c
HOVER_Result_t result = HoverboardApp_Resume();
```

RESUME成功后，示例会自动发送新的零运动帧。当前固件/ROS适配的安全语义是：RESUME只恢复RUN状态，不自动执行之前缓存的非零命令。

上层应用应在RESUME成功后确认安全，再调用 `HoverboardApp_SetCommand()` 设置新的运动命令。

### 7.3 ESTOP

设置ESTOP：

```c
HOVER_Result_t result = HoverboardApp_SetEstop(true);
```

解除ESTOP：

```c
HOVER_Result_t result = HoverboardApp_SetEstop(false);
```

ESTOP状态是锁存的：

- 普通运动帧不会产生电机运动。
- RELEASE和RESUME会被固件拒绝。
- 只有 `ESTOP(value=0)` 能解除。
- 解除后仍应先发送零帧，再恢复非零命令。

## 8. 读取反馈

反馈结构读取示例：

```c
HOVER_Feedback_t feedback;

if (HoverboardApp_ReadFeedback(&feedback)) {
  int16_t rightRpm = feedback.speedRightRpm;
  int16_t leftRpm = feedback.speedLeftRpm;
  float batteryVoltage = feedback.batteryVoltageX100 / 100.0f;
  float boardTemperature = feedback.boardTemperatureX10 / 10.0f;
  uint16_t driverState = feedback.driverState;
}
```

在线状态：

```c
if (!HoverboardApp_IsOnline()) {
  /* 停止发送非零命令，记录通信故障 */
  HoverboardApp_SetCommand(0, 0);
}
```

源码默认以100 ms作为反馈新鲜度判断。驱动器反馈周期约10 ms，连续超过100 ms没有合法反馈应视为通信异常。

反馈字段：

| 字段 | 单位 |
|---|---|
| `cmd1/cmd2` | 当前固件输入命令 |
| `speedRightRpm/speedLeftRpm` | rpm |
| `wheelRightCount/wheelLeftCount` | 编码器累计值，约0~8999循环 |
| `batteryVoltageX100` | 电压乘100 |
| `boardTemperatureX10` | 摄氏度乘10 |
| `driverState` | 0=RUN，1=RELEASE，2=ESTOP |
| `controlAck` | 最近一次控制命令ACK |

## 9. 控制周期建议

推荐主循环或RTOS任务按以下频率运行：

```text
运动帧：50 Hz，即每20 ms一帧
反馈解析：由UART接收中断持续执行
在线判断：50~100 ms
控制命令ACK等待：单次150 ms，最多3次重试
```

运动帧不能只发送一次。只发送一次后约0.8秒会触发驱动器USART超时并进入 `OPEN_MODE`。

发送RELEASE、RESUME或ESTOP时，应用应先将目标命令设置为零，控制命令完成后再恢复周期运动任务。

## 10. 结果码和故障排查

```c
const char *text = HOVER_ResultString(result);
```

结果码：

| 结果 | 含义 |
|---|---|
| `HOVER_RESULT_OK` | 操作成功 |
| `HOVER_RESULT_INVALID_ARGUMENT` | 参数错误 |
| `HOVER_RESULT_UART_ERROR` | UART发送或接收错误 |
| `HOVER_RESULT_ACK_TIMEOUT` | 未收到匹配的新ACK |
| `HOVER_RESULT_REJECTED` | 固件拒绝控制命令，例如ESTOP期间RESUME |
| `HOVER_RESULT_UNEXPECTED_STATE` | ACK接受但反馈状态不符合预期 |

排查顺序：

1. 确认TX/RX交叉连接。
2. 确认H723和驱动器共地。
3. 确认电平为3.3 V TTL。
4. 确认两端均为115200、8N1、无流控。
5. 用逻辑分析仪确认H723每20 ms发送8字节运动帧。
6. 确认驱动器返回26字节反馈帧，而不是旧版22字节帧。
7. 检查 `checksumErrorCount` 和 `uartErrorCount`。
8. 首次测试只发送零帧，再逐步增加命令值。

统计计数读取示例：

```c
uint32_t feedbackFrames;
uint32_t checksumErrors;
uint32_t uartErrors;

HoverboardApp_GetStatistics(&feedbackFrames,
                            &checksumErrors, &uartErrors);
```

## 11. 重要限制

- 当前代码使用 `HAL_UART_Receive_IT()` 每次接收1字节，115200 baud下对H723负载很低，且避免DMA与D-Cache配置问题。
- 如果后续改成DMA接收，H723必须处理D-Cache一致性，并确保DMA缓冲区位于DMA可访问且非缓存区域。
- 当前RELEASE和ESTOP是软件VLT_MODE零输出，不等价于机械制动、接触器断电或安全认证的硬件急停。
- 驱动器当前固件仍可能同时配置PWM辅助输入，但本H723控制源码完全不生成PWM，也不参与PWM手势切换。
- 如果PWM端已经接管驱动器，H723发送USART帧只会保持USART在线，不会立即抢回PWM控制权；需要等待固件PWM退出条件满足后才切回USART。

## 12. 验收清单

1. H723工程目标芯片确认为 `STM32H723VGT6`。
2. UART配置为115200、8N1、无流控。
3. UART全局中断已启用。
4. TX/RX交叉且共地。
5. 上电后持续发送零运动帧。
6. 能稳定解析26字节反馈并通过checksum。
7. 发送低幅前进、后退、左转、右转命令方向正确。
8. RELEASE收到正确ACK并进入RELEASE。
9. RESUME成功后保持零速，新的运动命令才恢复运动。
10. ESTOP锁存后RESUME被拒绝。
11. `set_estop(false)`能解除ESTOP。
12. 拔掉串口后应用识别反馈超时并停止非零命令。
