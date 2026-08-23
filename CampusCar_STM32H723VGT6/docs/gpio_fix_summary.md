# 舵机GPIO配置修复说明

## 问题描述

舵机不响应控制指令，虽然代码逻辑和PWM参数配置都正确。

## 根本原因

**TIM2的GPIO引脚（PA0）没有配置为复用功能**

虽然TIM2的时钟已使能，PWM内部工作正常，但PA0引脚仍处于默认状态（未配置为AF模式），导致PWM信号无法输出到物理引脚。

## 修复内容

### 修改文件
`Core/Src/tim.c` - `HAL_TIM_PWM_MspInit()` 函数

### 添加的代码
```c
void HAL_TIM_PWM_MspInit(TIM_HandleTypeDef* tim_pwmHandle)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  if(tim_pwmHandle->Instance==TIM2)
  {
    /* TIM2 clock enable */
    __HAL_RCC_TIM2_CLK_ENABLE();

    /* TIM2 GPIO Configuration: PA0 -> TIM2_CH1 (舵机PWM输出) */
    __HAL_RCC_GPIOA_CLK_ENABLE();
    GPIO_InitStruct.Pin = GPIO_PIN_0;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;      // 复用推挽输出
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStruct.Alternate = GPIO_AF1_TIM2;   // PA0的TIM2复用功能
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
  }
}
```

## 技术细节

### GPIO配置说明
- **Mode**: `GPIO_MODE_AF_PP` - 复用推挽输出模式
- **Alternate**: `GPIO_AF1_TIM2` - PA0的TIM2复用功能（根据STM32H723数据手册）
- **Speed**: `GPIO_SPEED_FREQ_LOW` - 50Hz PWM不需要高速
- **Pull**: `GPIO_NOPULL` - 无上下拉（舵机内部有输入电阻）

### 时钟验证
- TIM2_CLK = 192 MHz（从CubeMX配置确认）
- PSC = 191 → 计数频率 = 192MHz / 192 = 1MHz
- 1个计数 = 1μs（精确）
- ARR = 19999 → PWM频率 = 50Hz

## 验证方法

1. **编译并烧录固件**
2. **上电观察**：
   - PC13 LED闪烁4次（启动测试）
   - 舵机执行6阶段测试序列（0°→45°→90°→135°→180°→90°）
   - 进入主循环后舵机持续扫描30°~90°
3. **示波器测量**（可选）：
   - PA0应输出50Hz PWM波形
   - 脉宽范围0.5ms~2.5ms

## 为什么会漏配置

可能原因：
1. 在CubeMX中配置TIM2时，选择了"Internal Clock Only"
2. 没有在Pinout视图中激活TIM2_CH1引脚
3. 手动添加舵机代码时，只关注了TIM配置，忘记了GPIO初始化

## 修复时间

2026-08-22
