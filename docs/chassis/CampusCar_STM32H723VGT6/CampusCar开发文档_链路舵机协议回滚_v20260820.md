# CampusCar 开发文档（链路总览 + 舵机 + 协议 + 资源 + 回滚方案）

> 更新时间：2026-08-20
> 当前主推方案：**USART 串口直控电调**（PWM 方案代码保留，注释挂起，可随时回滚）

---

## 1. 项目控制链路总览（当前状态 v20260820）

### 1.1 整体数据流拓扑

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                              NUC (Q413)                                │
 │                                                                        │
 │  ┌────────────┐      ┌──────────────────────┐      ┌────────────────┐  │
 │  │ UE5 / 键盘 │─────▶│  ue_bridge / cmd_vel  │─────▶│ hoverboard_    │  │
 │  │  rosbridge │      │  运动学解算节点       │      │ driver C++     │  │
 │  └────────────┘      └──────────────────────┘      │ (或 Python 桥)  │  │
 │                                                     └───────┬────────┘  │
 │  ┌────────────┐      ┌──────────────────────┐                │           │
 │  │ Hikrobot   │─────▶│  路面缺陷检测 (YOLO)  │                │ 0xABCD   │
 │  │ 工业相机    │      │  bbox覆盖率/置信度    │                │ 0xABCE   │
 │  └────────────┘      └──────────┬───────────┘                │ 0xABCF   │
 │                                 │ 判定识别不全？              + 打包到帧  │
 │                                 ▼                              │           │
 │                       ┌──────────────────────┐                │           │
 │                       │ 舵机决策节点(节流+平滑)│◀──/servo_pitch─┤           │
 │                       │ 调 3~5°，≥ 500ms一次 │                │           │
 │                       └──────────┬───────────┘                │           │
 │                                  │ 角度命令                    │           │
 └──────────────────────────────────│────────────────────────────│───────────┘
                                    │                            │
                              USB-TTL (115200 8N1)             USB-TTL
                                    │                            │
 ┌──────────────────────────────────│────────────────────────────│───────────┐
 │                         STM32 H723VGT6 (DM-MC02)                        │
 │                                                                           │
 │  USART1 RX PA10 ←──────────NUC 命令字节流──────────→ USART1 TX PA09      │
 │                    │                                                      │
 │                    ▼                                                      │
 │         parse_command() 帧头分派器：                                      │
 │           ├── 0xABCD 运动帧（CH1/CH3 PWM 或 UART7 转发）  ← 主推切换    │
 │           ├── 0xABCE 控制帧（RELEASE/RESUME/ESTOP）      ← 老板固件      │
 │           └── 0xABCF 舵机帧（servo pitch 0~180°）        ← 新增         │
 │                                                                           │
 │  【主推】UART7 (连电调)         【挂起/备用】TIM1 PWM (PE9/13)           │
 │   TX PE8 ─────→ PA3 电调 RX      CH1 PE9 ──X── 电调 CH1 速度(可回滚)      │
 │   RX PE7 ←───── PA2 电调 TX      CH3 PE13──X── 电调 CH2 转向(可回滚)     │
 │   GND  ──────── 电调 GND         CH4 PE14 ──→ MG996R 舵机 PWM(仍保留)    │
 │                                                                           │
 │  TIM1 配置保留 50Hz(PSC=199 ARR=19999)，不改动时钟，只启用需要的通道     │
 └───────────────────────────────────────────────────────────────────────────┘
                                    │
                              3.3V TTL UART
                                    │
 ┌──────────────────────────────────│───────────────────────────────────────┐
 │                           电调驱动板 (F103)                              │
 │  固件内部 FOC 控制 + 0.8s 超时保护 + RELEASE/RESUME/ESTOP 状态机        │
 │  每 10ms 回传 26 字节真实反馈 (RPM/编码器/电压/温度/状态/ACK)           │
 └───────────────────────────────────────────────────────────────────────────┘
```

### 1.2 当前主推 vs 备用方案

| 方案 | 状态 | 链路 | 切换/回滚方式 |
|------|------|------|--------------|
| **方案A：UART7 串口直控电调** | **主推（开发中）** | NUC→UART1→STM32→UART7→电调 | 见 §3 |
| **方案B：TIM1 PWM 控制电调** | 挂起（代码注释保留） | NUC→UART1→STM32→TIM1 PWM→电调CH1/CH2 | 见 §2 |
| 舵机 TIM1_CH4 PWM | 可用（并行于任一方案） | NUC→UART1(0xABCF)→STM32→TIM1 CH4→MG996R | 永久保留 |

> ⚠️ PWM 代码 **不删除**，全部加 `/* ROLLBACK-PWM-BEGIN */ ... /* ROLLBACK-PWM-END */` 注释块，回滚时只需反注释。

---

## 2. PWM 方案代码保留与回滚说明

### 2.1 代码注释策略（所有改动标记 `ROLLBACK-PWM`）

涉及文件：**仅 main.c（不改 Cube 生成的 tim.c/usart.c/gpio.c）**

```c
/* 保持不动：TIM1 50Hz 初始化、GPIO AF 配置
   保留原因：舵机仍复用 TIM1 时钟/PWM模式；回滚PWM电调时不用改 tim.c */
MX_TIM1_Init();

/* ROLLBACK-PWM-BEGIN -----------------------------------------------------------
 * 以下为 PWM 方案的执行路径，当前主推串口直控，暂时挂起注释。
 * 回滚方法：1) 删除本注释块两头的 #if 0 / #endif
 *          2) 同时把 §3 的 UART7 路径注释或条件编译关闭
 *          3) 接线从 UART7(PE7/8) 切回电调 CH1/CH2 (PE9/13)
 *          4) 上电自动执行 9 步手势序列 (esc_gesture_init)
 *------------------------------------------------------------------------- */
#if 0
    /* 启动 TIM1 PWM 输出和 MOE 使能（电调 PWM 通道） */
    pwm_init();
    /* 电调 9 步手势初始化序列 (PWM 模式切换) */
    esc_gesture_init();
    /* 命令→PWM 应用 */
    apply_command_to_pwm(&cmd);
#endif
/* ROLLBACK-PWM-END ----------------------------------------------------------- */

/* 舵机 PWM (TIM1_CH4 PE14) 与电调方案无关，任何时候都执行 */
servo_init();
servo_set_angle(90);
```

> 在 `parse_command()` / `while(1)` 主循环中同样按上面的块格式，把 **PWM 专用执行路径**（apply_command_to_pwm、手势初始化调用、PWM 测试序列）全部包在 `#if 0` 里。函数定义本身（如 `pwm_init`、`esc_gesture_init`）**保留不动**，只是不在主路径被调用。这样编译器不会产生任何未引用符号，也方便日后一步解注释。

### 2.2 硬件回滚步骤（配合代码）

```
现状（串口方案）：                → 切回 PWM：
  STM32 PE8 → 电调 PA3              1. STM32 PE9 → 电调 CH1 (速度)
  STM32 PE7 ← 电调 PA2              2. STM32 PE13 → 电调 CH2 (转向)
  GND 接电调 GND                    3. GND 仍然保持共地
                                    4. main.c ROLLBACK-PWM 块反注释
                                    5. 上电：先 9 步手势 → PWM 模式接管
```

**为什么保留？** 串口方案虽然更好，但 UART7 路径尚未实车验证。若出现电调固件版本不支持串口、电平不兼容、20ms 心跳维护异常等任何意外，**5 分钟内切回 PWM（已实车验证过）** 不阻塞项目进度。

---

## 3. 主推方案：STM32 UART7 串口直控电调

### 3.1 STM32 资源分配表（当前 + 规划，保证不冲突）

| 外设 | 引脚 | 当前用途 | 备注 |
|------|------|---------|------|
| **USART1** | PA9=TX, PA10=RX | ✅ 连 NUC USB-TTL | 115200 8N1，开中断，不换 |
| **UART7** | PE8=TX, PE7=RX | 🛠 连电调 USART2(PA3/PA2) | **新增：115200 8N1，开中断** |
| USART2 | PD5/PD6, DE=PD4 | ❌ 板载 RS485，不用 | 电平已转差分 |
| USART3 | PD8/PD9, DE=PB14 | ❌ 板载 RS485，不用 | 电平已转差分 |
| UART10 | PE3=TX, PE2=RX | 备用 | TTL 端子排，UART7出问题就换这个 |
| **TIM1**（50Hz, PSC=199, ARR=19999） | | ✅ 保持初始化 | 舵机复用，PWM回滚复用 |
| TIM1 CH1 | PE9 | ⏸ PWM 电调速度 (挂起) | 回滚时启用 |
| TIM1 CH2 | PE11 | 空闲 | 备用舵机(左右Yaw) |
| TIM1 CH3 | PE13 | ⏸ PWM 电调转向 (挂起) | 回滚时启用 |
| TIM1 CH4 | **PE14** | ✅ MG996R 舵机 Pitch | **已接入，复用 TIM1** |
| PC13 LED | PC13 | ✅ 上电闪 4 次 | 启动标记 |
| PC14 LED | PC14 | ✅ 在线/错误状态闪烁 | 调试保留 |
| CAN3 | PD12/PD13 | 未用 | 后续 CAN 设备备用 |

### 3.2 UART7 CubeMX 新增配置

在现有 `.ioc` 只改这两项（不改 UART1，不改 TIM1）：

1. **Connectivity → UART7：** Mode = **Asynchronous**，BaudRate=115200, 8N1, No Hardware Flow
2. **NVIC Settings：** 勾选 **UART7 global interrupt**（Enable，抢占优先级 5 或与 UART1 同级）
3. **生成代码**：会得到 `MX_UART7_Init()` 和 `huart7` 句柄

如果不想动 `.ioc`（保守），用 **纯代码手动初始化**（放在 `USER CODE BEGIN 2` 区域，与 PWM 挂起块并列），见 [串口直控方案说明.md §5.5](file:///e:/CyberProject/CampusCar/串口直控方案说明.md#L257)。

### 3.3 STM32 集成老板的源码（后续实现步骤占位，待测试工具验证通过后再写）

```
步骤 1: 源码导入 Core/Inc 与 Core/Src 目录
步骤 2: hoverboard_usart_app_example.c 里把 huart1 改为 huart7
步骤 3: main.c USER CODE BEGIN 2 调用 HoverboardApp_Init()
步骤 4: 主循环 while(1) 每 1ms 调一次 HoverboardApp_20msTask()
步骤 5: NUC→UART1 命令 0xABCD 解析后调用 HoverboardApp_SetCommand()
步骤 6: 电调→UART7 反馈每 100~200ms 打包回传给 NUC (可选)
```

> 🔴 **在运行 `串口调试源码.exe` 直连电调 PA2/PA3 成功控制电机之前，不做上述集成。** 先验证电调固件侧通不通，避免瞎改 STM32。

---

## 4. MG996R 舵机控制方案（摄像头 Pitch 轴）

### 4.1 MG996R 规格与供电说明（已查证 DigiKey / TowerPro 官方数据）

| 参数 | 4.8V | 5V (实际常用) | 6V | 来源 |
|------|------|---------------|-----|------|
| **工作电压范围** | 4.8V ~ 7.2V 全范围可用 | ✅ 在范围内 | ✅ 最佳力矩 | DigiKey 官方 PDF |
| 堵转力矩 | 9.4 kg·cm | ~10 kg·cm | 11 kg·cm | DigiKey / TowerPro |
| **空载运行电流** | ~170 mA | ~200 mA | ~250 mA | Adeept / ThinkRobotics |
| **带载运行电流** | ~500 mA | ~600 mA | 800~900 mA | DigiKey (6V 值) |
| **堵转电流（最危险）** | **~1.5 ~ 1.8 A** | **~1.8 ~ 2.0 A** | **2.2 ~ 2.5 A** | Adeept ±10% 规格 / ThinkRobotics 1.4A（clone 有差异）|
| 舵机 PWM 周期 | 20ms / 50Hz（与 TIM1 当前完全一致） | 同 | 同 | 通用规格 |
| 脉宽范围 | **500us (0°) ~ 2500us (180°)，中位 1500us (90°)** | 同 | 同 | 实验室测试验证 |
| 信号电平 | 标准 3.3V/5V TTL 兼容 | ✅ STM32 3.3V 直出可用 | ✅ | 通用规格 |

#### 结论：5V 可以接，但必须看"5V 的电源能力"

- ✅ **电压兼容**：5V 在 MG996R 官方 4.8~7.2V 工作范围内，工作力矩和速度都能满足摄像头俯仰轻负载需求（摄像头 < 100g，力矩剩很多）。
- ⚠️ **电流不能含糊**：**如果 STM32 板上的 5V 是直接来自 USB 口**，USB 规范仅 500mA（0.5A），一旦舵机堵转或快速扫动会拉到 **1.5A~2A**，超过 USB 限流会触发：
  1. 电脑 USB 端过流保护断开 → STM32 整体掉电重启
  2. 5V 电压塌陷 → STM32 复位 + SD 卡/USB 数据损坏风险
- ✅ **可以安全接 STM32 5V 的情况**：如果 DM-MC02 板上的 5V 来自 **DC 座的独立 DC-DC（如 MP1584 / XL4005，一般标称 2A~3A）**，5V 电源能力够，就可以直接把舵机 VCC 红线上到 STM32 的 5V 排针。
- 🟡 **稳健方案**：无论 5V 来源是什么，**推荐舵机电源线上串一颗 1A~2A 的自恢复保险丝（PPTC）**，并在 STM32 侧 5V/GND 间加 1000uF 以上的大电容做本地储能。

### 4.2 接线表（舵机 3P 接口，红=VCC，棕/黑=GND，橙/黄=PWM Signal）

| MG996R 线 | 接端 A（STM32 5V 直连方案，5V 有≥2A能力时） | 接端 B（独立 5V/6V 电源方案，更推荐） |
|----------|--------------------------------------------|--------------------------------------|
| 🔴 红线 (VCC) | STM32 板 5V 排针 (电流≥2A 确认) | **独立电源 +5~6V**（独立 5V/2A 适配器或锂电 BEC）|
| ⚫/🟤 黑线 (GND) | STM32 GND 排针 | **独立电源 GND + 另外用一根短线连到 STM32 GND（共地）** |
| 🟠 橙线 (Signal) | **STM32 PE14 (TIM1_CH4)** | **STM32 PE14 (TIM1_CH4)**（信号只有这一种接法） |

> 共地是**绝对必须的**。STM32 输出的 PWM 是以 STM32 GND 为参考的，如果舵机电源不共地，信号参考不同，舵机会乱转或不转。

### 4.3 STM32 侧代码（不重复 TIM1 已有配置）

**CubeMX 不用改（推荐，避免 .ioc 重生成风险）**，直接在 main.c 的 `USER CODE BEGIN 2` 区域加以下代码（与 PWM 挂起块并列）：

```c
/* ====== MG996R 舵机 Pitch (TIM1_CH4 → PE14) ======
 * 复用 TIM1 已有的 50Hz 配置 (PSC=199, ARR=19999 → 1 count = 1us)
 * 只启 CH4，不碰 CH1/CH3，不重复 MX_TIM1_Init，不重开时钟
 */
#define SERVO_TIM_CH         TIM_CHANNEL_4
#define SERVO_GPIO_PORT      GPIOE
#define SERVO_GPIO_PIN       GPIO_PIN_14
#define SERVO_PULSE_MIN      500U     /* 0.5ms → 0°   */
#define SERVO_PULSE_MID      1500U    /* 1.5ms → 90°  */
#define SERVO_PULSE_MAX      2500U    /* 2.5ms → 180° */
#define SERVO_ANGLE_MIN      0
#define SERVO_ANGLE_MAX      180
#define SERVO_ANGLE_SAFE_MIN 20       /* 机械限位，避免顶死结构 */
#define SERVO_ANGLE_SAFE_MAX 160

static void servo_init(void)
{
    /* PE14 → TIM1 AF1（仅改这一个 pin，不改 tim.c） */
    GPIO_InitTypeDef g = {0};
    /* GPIOE 时钟已在 TIM1 MspPostInit 里 __HAL_RCC_GPIOE_CLK_ENABLE()，不再重复使能 */
    g.Pin       = SERVO_GPIO_PIN;
    g.Mode      = GPIO_MODE_AF_PP;
    g.Pull      = GPIO_NOPULL;
    g.Speed     = GPIO_SPEED_FREQ_HIGH;
    g.Alternate = GPIO_AF1_TIM1;
    HAL_GPIO_Init(SERVO_GPIO_PORT, &g);

    /* 只额外 Config CH4（CH1/CH3 由 CubeMX 已经 Config 过，这里不重配） */
    TIM_OC_InitTypeDef oc = {0};
    oc.OCMode       = TIM_OCMODE_PWM1;
    oc.Pulse        = SERVO_PULSE_MID;   /* 上电默认 90° 中位 */
    oc.OCPolarity   = TIM_OCPOLARITY_HIGH;
    oc.OCFastMode   = TIM_OCFAST_DISABLE;
    HAL_TIM_PWM_ConfigChannel(&htim1, &oc, SERVO_TIM_CH);

    /* TIM1 主输出使能（如果 PWM 电调方案挂起后没调用过，补一次） */
    __HAL_TIM_MOE_ENABLE(&htim1);
    HAL_TIM_PWM_Start(&htim1, SERVO_TIM_CH);
}

/* 0~180° → 500~2500 线性映射（整数运算避免 float） */
static uint16_t servo_angle_to_pulse(uint8_t angle)
{
    if (angle < SERVO_ANGLE_SAFE_MIN) angle = SERVO_ANGLE_SAFE_MIN;
    if (angle > SERVO_ANGLE_SAFE_MAX) angle = SERVO_ANGLE_SAFE_MAX;
    uint32_t pulse = SERVO_PULSE_MIN +
        ((uint32_t)(angle - SERVO_ANGLE_MIN) * (SERVO_PULSE_MAX - SERVO_PULSE_MIN))
        / (SERVO_ANGLE_MAX - SERVO_ANGLE_MIN);
    return (uint16_t)pulse;
}

static void servo_set_angle(uint8_t angle)
{
    __HAL_TIM_SET_COMPARE(&htim1, SERVO_TIM_CH, servo_angle_to_pulse(angle));
}
```

> 机械结构装好后测量实际角度边界，修改 `SERVO_ANGLE_SAFE_MIN/MAX`，避免顶死外壳或扯断排线。

### 4.4 舵机闭环自动调整链路（路面缺陷检测 → 角度调整）

#### 链路数据流

```
Hikrobot /camera/image_raw (30fps)
        │
        ▼
NUC 缺陷检测节点 (YOLO/SAM)
   输出: bbox[x,y,w,h] + confidence + class=路面缺陷
        │
        ▼
NUC 决策节点 (Python, 规则判定 + 节流平滑)
   规则：
   ① bbox 触碰到画面底/顶 (y<=5 或 y+h>=IMG_H-5) → 需要向下/向上 Pitch
   ② confidence < 0.4 (漏检风险)                  → 试探 ±3° 小角度
   ③ bbox 覆盖率 < 20% (拍得太远不清晰)          → 向下 Pitch + 车靠近
   节流：两次舵机命令 ≥ 500ms，单次只调 3~5° 小步长
   平滑：每次目标值按 1°/50ms 渐进插值，不用一步到位
        │
        ▼
发布 /servo_pitch (std_msgs/Int16, 0~180)
        │
        ▼
NUC Python 桥接节点（uart_servo_bridge.py）
   把 angle 打包为 8 字节 0xABCF 帧（小端 XOR）→ /dev/ttyUSB0
        │
        ▼
STM32 USART1 RX
   parse_command() 分派 → 帧头 0xABCF → 校验通过 → servo_set_angle()
        │
        ▼
TIM1_CH4 PE14 PWM 输出 → MG996R → 摄像头 Pitch 改变
        │
        ▼
（下一次检测时重新判断 bbox 是否还触边 → 闭环收敛或停止）
```

#### 配套动作（可选，缺陷在画面外角度调不到）

若舵机已到机械极限仍拍不全，**同时发给 `/cmd_vel` 低速命令**，让车前后挪一点位置（向前挪 ↔ 俯仰向下，向后挪 ↔ 俯仰向上），形成双执行器闭环。

---

## 5. USART1（NUC↔STM32）协议扩展帧汇总

> 所有帧：小端序，波特率 115200，校验 = 帧头 XOR 数据字段 XOR（2字节 uint16），不新增任何算法。

| 帧头 | 结构（8 字节） | 字段含义 | 方向 | 状态 |
|------|---------------|----------|------|------|
| **0xABCD** (运动帧) | header(2) + steer(2) + speed(2) + checksum(2) | steer=-1000~+1000；speed=-1000~+1000 | NUC→STM32 | ✅ 实现 |
| **0xABCE** (控制帧) | header(2) + cmd(2) + value(2) + checksum(2) | cmd=1 RELEASE, 2 RESUME, 3 ESTOP(value=1锁存/0解除) | NUC→STM32→(转发UART7) | 老板源码已有实现 |
| **0xABCF** (舵机帧 ← 新增) | header(2) + pitch(2) + reserved(2) + checksum(2) | pitch=0~180；reserved=0（以后扩展Yaw/第2舵机） | NUC→STM32 | ✅ 协议已定，STM32解析分支写好 |
| **0xABD0** (STM32状态回传，可选扩展) | header(2) + cur_pitch(2) + driver_state(2) + checksum(2) | 周期回传当前舵机角度和电调状态 | STM32→NUC | 占位，后续实车联调再加 |

**帧头冲突检查**：0xABCD、0xABCE、0xABCF 三个 16-bit 帧头彼此不同（bit0 就不同），解析器用 `if-else if` 顺序判断不会混。

---

## 6. 推进顺序和待办（带验证前置条件，防止返工）

| 阶段 | 任务 | 前置条件 | 完成后标记 |
|------|------|---------|-----------|
| 🔹 Phase 0 | 用 `串口调试源码.exe` + USB-TTL 直连电调 PA2/PA3，电调接电池，验证前进/后退 | 无（现在就能做） | ☐ 电调固件串口通道确认通 |
| 🔹 Phase 1 | 舵机独立测试：STM32 接 MG996R（电源+信号+共地），上电跑 90°→0°→180°循环 | 无 | ☐ 舵机物理和 PWM 配置通过 |
| 🔹 Phase 2 | STM32 加上 0xABCF 舵机帧解析，Python 直接写串口控制角度 | Phase 1 + USART1 已工作 | ☐ NUC→舵机命令通路打通 |
| 🔹 Phase 3 | STM32 CubeMX 开 UART7 + 导入老板给的 4 个 controller 源码 | Phase 0 ✅（验证电调固件通） | ☐ STM32↔电调串口代码接好 |
| 🔹 Phase 4 | 主循环里调 HoverboardApp_20msTask()，电调保持零帧心跳 1 分钟，反馈帧稳定回传 | Phase 3 | ☐ 电调在线状态稳定 |
| 🔹 Phase 5 | NUC→USART1 发 0xABCD steer/speed，车底盘正确响应 | Phase 4 | ☐ NUC→车 完整控制链路打通 |
| 🔹 Phase 6 | 接入视觉缺陷检测节点 → 舵机闭环自动调整拍全缺陷 | Phase 2 + Phase 5 | ☐ 视觉-舵机闭环 |
| 🔹 Phase 7 | hoverboard_driver C++ 侧改为读取 26 字节反馈，发布 /odom/电压 | Phase 5 | ☐ ROS2 实车里程计可用 |
| 🔹 Rollback | 如果 Phase 3/4 出意外，按 §2.2 5 分钟切回 PWM 方案，不阻塞演示 | 任何阶段 | ☐ 回滚预案随时可用 |

---

## 7. 文档变更记录（便于随时回查）

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-08-19 | v0.1 | 起草串口直控方案 [串口直控方案说明.md](file:///e:/CyberProject/CampusCar/串口直控方案说明.md)，含 DE/AB 解析、协议、CubeMX 配置 |
| 2026-08-20 | v1.0 (本文档) | ① 确定主推串口、PWM 方案加 ROLLBACK 注释挂起（不删代码）<br>② MG996R 5V 供电查证 + 风险提示 + 两种接线方案<br>③ UART1 协议扩展 0xABCF 舵机帧头，三帧不冲突<br>④ 视觉缺陷→舵机自动调整链路完整数据流<br>⑤ 资源分配表不重复 TIM1/UART1 已有配置<br>⑥ 推进顺序 + 回滚步骤 |
| | | |

---

## 8. 快速代码位置索引（接手人定位）

| 功能 | 关键文件/位置 |
|------|-------------|
| TIM1 50Hz / PWM 配置 | [tim.c#L30-L107](file:///e:/CyberProject/CampusCar/CampusCar_STM32H723VGT6/Core/Src/tim.c#L30-L107)（保持不动） |
| PWM 电调挂起块 / 回滚块 | [main.c](file:///e:/CyberProject/CampusCar/CampusCar_STM32H723VGT6/Core/Src/main.c) 搜 `ROLLBACK-PWM` |
| 舵机初始化 + angle→PWM | [main.c](file:///e:/CyberProject/CampusCar/CampusCar_STM32H723VGT6/Core/Src/main.c) 搜 `SERVO_TIM_CH` |
| UART1 115200 配置 | [usart.c](file:///e:/CyberProject/CampusCar/CampusCar_STM32H723VGT6/Core/Src/usart.c) |
| 0xABCD 运动帧解析 | main.c 搜 `parse_command` |
| 0xABCF 舵机帧解析分支 | main.c 搜 `FRAME_HEADER_SERVO` |
| 电调串口直控源码（老板） | [hoverboard_usart_controller.c](file:///e:/CyberProject/CampusCar/STM32H723_USART_Controller/Core/Src/hoverboard_usart_controller.c) / .h |
| hoverboard_driver C++ | [hoverboard_driver.cpp](file:///e:/CyberProject/CampusCar/campusCar-hardware-new-stm32-hikrobot/hardware/hoverboard_driver/hardware/hoverboard_driver.cpp) |
| NUC Python UART 测试脚本 | [test_hoverboard_uart.py](file:///e:/CyberProject/CampusCar/campusCar-hardware-new-stm32-hikrobot/scripts/test_hoverboard_uart.py) |
| 协议帧格式说明 | [串口协议说明.md](file:///e:/CyberProject/CampusCar/串口协议说明.md) |
| 完整串口直控方案 | [串口直控方案说明.md](file:///e:/CyberProject/CampusCar/串口直控方案说明.md) |
