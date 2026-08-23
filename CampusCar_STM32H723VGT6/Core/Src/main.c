/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  * @note           : 固定 PWM 测试程序 - 上电后直接输出固定 PWM 值
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "hoverboard_usart_app_example.h"  /* 串口直控电调库 (UART7) */
#include "servo_controller.h"              /* 舵机控制模块 */
#include "esc_pwm_controller.h"            /* PWM 控制模块（备用） */
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* ====== 串口协议定义 ====== */
#define FRAME_HEADER         0xABCD  /* 帧头 */
#define SERIAL_COMMAND_SIZE  10      /* 命令帧长度 (扩展10字节：支持舵机控制) */

/* ====== PWM 参数 (STM32H723: TIM1时钟=200MHz, PSC=199 → 1MHz 计数) ====== */
/* 1 个计数 = 1μs，所以 1000 计数=1.0ms, 1500 计数=1.5ms(停止), 2000 计数=2.0ms */
#define PWM_STOP_VALUE      1500U    /* 1.5ms 脉宽 = 停止/中位 */
#define PWM_MIN_VALUE       1000U    /* 1.0ms 脉宽 = 最大反向/最大右转 */
#define PWM_MAX_VALUE       2000U    /* 2.0ms 脉宽 = 最大前进/最大左转 */

/* ====== 命令值范围 (hoverboard 协议 speed/steer 的范围) ====== */
#define SERIAL_FEEDBACK_SIZE 16      /* 反馈帧长度 */
#define FEEDBACK_PERIOD_MS   200     /* 反馈周期 */
#define COMMAND_MIN          (-1000) /* 命令最小值 */
#define COMMAND_MAX          1000     /* 命令最大值 */

/* ====== MG996R 舵机参数 (TIM2: 50Hz PSC=199 ARR=19999 → 1 count=1μs) ====== */
/* MG996R 180° 舵机：0.5ms=0° / 1.5ms=90°(中位) / 2.5ms=180° */
#define SERVO_PULSE_MIN       500U    /* 0.5ms → 0° */
#define SERVO_PULSE_MID       1500U   /* 1.5ms → 90° (中位) */
#define SERVO_PULSE_MAX       2500U   /* 2.5ms → 180° */

/* 安全角度范围：留机械余量，避免顶死结构 */
#define SERVO_ANGLE_SAFE_MIN  20      /* 最小 20° */
#define SERVO_ANGLE_SAFE_MAX  160     /* 最大 160° */
#define SERVO_ANGLE_MID       90      /* 中位 90° */

/* 舵机使用的定时器和通道：TIM2_CH1 → PA00 (板上丝印 RA00 对应 TIM2_CH1) */
#define SERVO_HTIM            htim2
#define SERVO_TIM_CH          TIM_CHANNEL_1

/* ====== 舵机三档位定义 ====== */
#define SERVO_GEAR_1    60   /* 档位1：60度 */
#define SERVO_GEAR_2    90   /* 档位2：90度中位 */
#define SERVO_GEAR_3    120  /* 档位3：120度 */

static uint8_t current_gear = 1;  /* 当前档位 */
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */
/* 命令帧结构 (10 字节) - 扩展hoverboard协议，支持舵机控制 */
typedef struct __attribute__((packed)) {
    uint16_t start;       /* 帧头 0xABCD */
    int16_t  steer;       /* 转向命令 (-1000~1000) */
    int16_t  speed;       /* 速度命令 (-1000~1000) */
    uint8_t  servo_gear;  /* 舵机档位 (1/2/3, 0表示不改变) */
    uint8_t  reserved;    /* 保留字段 */
    uint16_t checksum;    /* XOR 校验和 */
} SerialCommand;

/* 反馈帧结构体 (小端序, 16 字节, 与 NUC 侧 SerialFeedbackCompact 一致) */
/* 驱动用 compact 格式, 不含编码器和电流字段 */
typedef struct {
    uint16_t start;       /* 0xABCD */
    int16_t  cmd1;        /* 回显 steer 命令 */
    int16_t  cmd2;        /* 回显 speed 命令 */
    int16_t  speedR_meas; /* 右轮转速 RPM (STM32 无传感器, 填 0) */
    int16_t  speedL_meas; /* 左轮转速 RPM (STM32 无传感器, 填 0) */
    int16_t  batVoltage;  /* 电池电压, 单位 0.01V (如 2400=24.0V) */
    int16_t  boardTemp;   /* 板温, 单位 0.1°C (如 250=25.0°C) */
    uint16_t cmdLed;      /* LED 命令 (0) */
    uint16_t checksum;    /* 校验和 = 上面所有字段 XOR */
} SerialFeedbackCompact;
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MPU_Config(void);
/* USER CODE BEGIN PFP */
static void debug_print(const char *str);
static int parse_command(const uint8_t *data, SerialCommand *cmd);
static void send_feedback(const SerialCommand *cmd);
static void led_stage(uint8_t stage_num);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
/* 串口调试输出函数 */
static void debug_print(const char *str)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)str, (uint16_t)strlen(str), 200);
}

/* 解析 hoverboard 协议命令（10字节，支持舵机），返回值：0=成功, 1=帧头错误, 2=校验错误 */
static int parse_command(const uint8_t *data, SerialCommand *cmd)
{
    uint16_t checksum_calc;
    char buf[80];

    /* 打印接收到的原始数据 */
    snprintf(buf, sizeof(buf),
             "\r\n[RX] %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X\r\n",
             data[0], data[1], data[2], data[3], data[4], 
             data[5], data[6], data[7], data[8], data[9]);
    debug_print(buf);

    /* 检查帧头 */
    cmd->start = (uint16_t)data[0] | ((uint16_t)data[1] << 8);
    if (cmd->start != FRAME_HEADER) {
        snprintf(buf, sizeof(buf),
                 "[ERR] Header: got 0x%04X, expect 0x%04X\r\n",
                 cmd->start, FRAME_HEADER);
        debug_print(buf);
        return 1;  /* 帧头错误 */
    }

    /* 解析数据 */
    cmd->steer = (int16_t)((uint16_t)data[2] | ((uint16_t)data[3] << 8));
    cmd->speed = (int16_t)((uint16_t)data[4] | ((uint16_t)data[5] << 8));
    cmd->servo_gear = data[6];  /* 舵机档位 */
    cmd->reserved = data[7];    /* 保留 */
    cmd->checksum = (uint16_t)data[8] | ((uint16_t)data[9] << 8);

    /* XOR 校验：start ^ steer ^ speed ^ servo_gear ^ reserved */
    checksum_calc = cmd->start ^ 
                    (uint16_t)cmd->steer ^ 
                    (uint16_t)cmd->speed ^ 
                    ((uint16_t)cmd->servo_gear | ((uint16_t)cmd->reserved << 8));
    
    if (cmd->checksum != checksum_calc) {
        snprintf(buf, sizeof(buf),
                 "[ERR] Checksum: got 0x%04X, calc 0x%04X\r\n",
                 cmd->checksum, checksum_calc);
        debug_print(buf);
        return 2;  /* 校验错误 */
    }

    /* 限制范围 */
    if (cmd->steer > COMMAND_MAX) cmd->steer = COMMAND_MAX;
    if (cmd->steer < COMMAND_MIN) cmd->steer = COMMAND_MIN;
    if (cmd->speed > COMMAND_MAX) cmd->speed = COMMAND_MAX;
    if (cmd->speed < COMMAND_MIN) cmd->speed = COMMAND_MIN;

    /* 打印解析结果 */
    snprintf(buf, sizeof(buf),
             "[OK] steer=%d speed=%d servo_gear=%d\r\n",
             cmd->steer, cmd->speed, cmd->servo_gear);
    debug_print(buf);

    return 0;  /* 成功 */
}

/* 发送反馈帧给 NUC (SerialFeedbackCompact, 16 字节) */
/* 驱动需要收到反馈帧才会判定为 "connected"，否则显示离线 */
static void send_feedback(const SerialCommand *cmd)
{
    SerialFeedbackCompact fb;
    fb.start       = FRAME_HEADER;
    fb.cmd1        = cmd->steer;        /* 回显转向命令 */
    fb.cmd2        = cmd->speed;        /* 回显速度命令 */
    fb.speedR_meas = 0;                /* 无轮速传感器 */
    fb.speedL_meas = 0;
    fb.batVoltage  = 2400;              /* 24.0V 占位 (实际无 ADC 采集) */
    fb.boardTemp   = 250;               /* 25.0°C 占位 */
    fb.cmdLed      = 0;

    /* 校验和 = 所有字段 XOR (与 NUC 驱动一致) */
    fb.checksum = (uint16_t)(fb.start ^
                             (uint16_t)fb.cmd1 ^
                             (uint16_t)fb.cmd2 ^
                             (uint16_t)fb.speedR_meas ^
                             (uint16_t)fb.speedL_meas ^
                             (uint16_t)fb.batVoltage ^
                             (uint16_t)fb.boardTemp ^
                             fb.cmdLed);

    /* 通过 UART1 发送 16 字节反馈帧 */
    HAL_UART_Transmit(&huart1, (uint8_t *)&fb, SERIAL_FEEDBACK_SIZE, 100);
}

/* LED 阶段指示函数 */
static void led_stage(uint8_t stage_num)
{
    char buf[40];
    if (stage_num == 0) stage_num = 1;
    if (stage_num > 9)  stage_num = 9;

    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);  /* 先关 LED，保证从灭开始 */
    HAL_Delay(600);

    for (uint8_t i = 0; i < stage_num; i++) {
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
        HAL_Delay(120);
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
        HAL_Delay(120);
    }

    snprintf(buf, sizeof(buf), "[STAGE] === %u ===\r\n", (unsigned)stage_num);
    debug_print(buf);
}

/**
 * @brief 切换舵机档位
 * @param gear 档位 (1/2/3)
 */
void Servo_SetGear(uint8_t gear)
{
    uint8_t target_angle = SERVO_GEAR_1;
    
    switch(gear) {
        case 1:
            target_angle = SERVO_GEAR_1;
            current_gear = 1;
            break;
        case 2:
            target_angle = SERVO_GEAR_2;
            current_gear = 2;
            break;
        case 3:
            target_angle = SERVO_GEAR_3;
            current_gear = 3;
            break;
        default:
            return;  /* 无效档位 */
    }
    
    Servo_SetAngle(target_angle);
    
    /* 通过串口反馈当前档位 */
    char msg[50];
    snprintf(msg, sizeof(msg), "[SERVO] Gear %d -> %d°\r\n", gear, target_angle);
    debug_print(msg);
}

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MPU Configuration--------------------------------------------------------*/
  MPU_Config();

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_USART1_UART_Init();
  MX_UART7_Init();        /* UART7 连接电调 (PE7 RX / PE8 TX) */
  MX_TIM1_Init();
  MX_TIM2_Init();
  /* USER CODE BEGIN 2 */

  /* 配置 PC13 和 PC14 */
  {
    GPIO_InitTypeDef GPIO_InitStruct_LED = {0};
    GPIO_InitStruct_LED.Pin = GPIO_PIN_13 | GPIO_PIN_14;
    GPIO_InitStruct_LED.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct_LED.Pull = GPIO_NOPULL;
    GPIO_InitStruct_LED.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct_LED);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_RESET);
  }

  /* PC13 闪 4 次 */
  for (int i = 0; i < 4; i++) {
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
    HAL_Delay(200);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
    HAL_Delay(200);
  }

  /* ============== 舵机初始化和测试（使用新模块）============== */
  debug_print("[SERVO] Init MG996R servo on TIM2_CH1 (PA00)...\r\n");
  if (Servo_Init() != 0) {
    debug_print("[ERR] Servo init failed!\r\n");
  } else {
    debug_print("[SERVO] Init OK.\r\n");
    
    /* 三档位测试：每个档位停留1秒 */
    debug_print("[SERVO] Testing 3 gears...\r\n");
    
    debug_print("[SERVO] Gear 1 -> 60°\r\n");
    Servo_SetGear(1);
    HAL_Delay(1000);
    
    debug_print("[SERVO] Gear 2 -> 90°\r\n");
    Servo_SetGear(2);
    HAL_Delay(1000);
    
    debug_print("[SERVO] Gear 3 -> 120°\r\n");
    Servo_SetGear(3);
    HAL_Delay(1000);
    
    /* 测试完成，回到档位2（中位） */
    debug_print("[SERVO] Test complete, back to Gear 2 (90°)\r\n");
    Servo_SetGear(2);
    
    debug_print("[SERVO] Ready for control via UART protocol.\r\n");
  }

/* ROLLBACK-PWM-BEGIN (使用新模块) */
#if 0
  ESC_PWM_Init();
  HAL_Delay(1000);
  ESC_PWM_GestureInit();
#endif
/* ROLLBACK-PWM-END */

  /* ============== UART7 串口直控方案（主推方案，已集成） ============== */
  /* UART7 (PE7 RX / PE8 TX) 连接电调 USART2 (PA3 RX / PA2 TX)
   * 功能：
   *   - 启动 UART7 接收中断，解析电调 26 字节反馈帧
   *   - 发送首帧零命令，激活电调在线状态
   *   - 主循环中每 20ms 自动发送心跳帧（由 HoverboardApp_20msTask 管理）
   * 注意：
   *   - 不需要 PWM 手势初始化
   *   - 电调固件 0.8s 超时保护 + STM32 100ms 新鲜度检查双重安全
   *   - UART1 保持连接 NUC，不冲突 */
  debug_print("[UART7] Init ESC controller (USART direct mode)...\r\n");
  HoverboardApp_Init();  /* 启动 UART7 串口直控 */
  debug_print("[UART7] ESC controller started. 20ms heartbeat active.\r\n");

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
/* ROLLBACK-PWM-2-BEGIN -------------------------------------------------------
 * PWM 方案上电一次测试序列（前进2s→后退2s→左转2s→右转2s）。
 * 回滚时将 #if 0 → #if 1 启用；串口方案保持关闭避免一上电就跑。
 *------------------------------------------------------------------------- */
#if 0
  /* 先执行一次测试：前进→后退→左转→右转 */
  {
    /* 前进 2 秒 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, PWM_MAX_VALUE);  /* 2.0ms 前进 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, PWM_STOP_VALUE);  /* 1.5ms 直行 */
    HAL_Delay(2000);
    
    /* 停止 0.5 秒 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, PWM_STOP_VALUE);
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, PWM_STOP_VALUE);
    HAL_Delay(500);
    
    /* 后退 2 秒 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, PWM_MIN_VALUE);   /* 1.0ms 后退 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, PWM_STOP_VALUE);  /* 1.5ms 直行 */
    HAL_Delay(2000);
    
    /* 停止 0.5 秒 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, PWM_STOP_VALUE);
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, PWM_STOP_VALUE);
    HAL_Delay(500);
    
    /* 左转 2 秒 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, PWM_STOP_VALUE);  /* 1.5ms 停止 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, PWM_MAX_VALUE);   /* 2.0ms 左转 */
    HAL_Delay(2000);
    
    /* 停止 0.5 秒 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, PWM_STOP_VALUE);
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, PWM_STOP_VALUE);
    HAL_Delay(500);
    
    /* 右转 2 秒 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, PWM_STOP_VALUE);  /* 1.5ms 停止 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, PWM_MIN_VALUE);   /* 1.0ms 右转 */
    HAL_Delay(2000);
    
    /* 停止位置 */
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, PWM_STOP_VALUE);
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, PWM_STOP_VALUE);
  }

  /* 测试完成，发送提示 */
  HAL_UART_Transmit(&huart1, (uint8_t*)"Test Done, Waiting for UART...\r\n", 31, 100);
  debug_print("Send: AB CD 00 00 E8 03 9D 9A (forward)\r\n");
#endif
/* ROLLBACK-PWM-2-END ----------------------------------------------------------- */

  /* 主循环：PC14 闪烁 + 等待串口命令 + UART7 心跳 + 反馈帧 + 舵机控制 */
  uint32_t last_led_tick = HAL_GetTick();
  uint32_t last_cmd_tick = HAL_GetTick();
  uint32_t last_feedback_tick = HAL_GetTick();
  uint8_t cmd_buffer[SERIAL_COMMAND_SIZE] = {0};
  SerialCommand current_cmd = {0};

  while (1)
  {
    /* ========== UART7 串口直控 20ms 心跳任务（必须每 1ms 调用一次） ========== */
    HoverboardApp_20msTask();  /* 自动管理 20ms 发帧 + 100ms 超时保护 */

    /* PC14 持续闪烁 */
    uint32_t current_tick = HAL_GetTick();
    if ((current_tick - last_led_tick) >= 500)
    {
      last_led_tick = current_tick;
      HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_14);
    }

    /* 等待串口命令（改为非阻塞，超时1ms） */
    if (HAL_UART_Receive(&huart1, cmd_buffer, SERIAL_COMMAND_SIZE, 1) == HAL_OK)
    {
      /* 收到 10 字节数据，解析命令 */
      int result = parse_command(cmd_buffer, &current_cmd);
      if (result == 0)
      {
/* ROLLBACK-PWM-3-BEGIN (使用新模块) */
#if 0
        ESC_PWM_ApplyCommand(current_cmd.steer, current_cmd.speed);
#else
        HoverboardApp_SetCommand(current_cmd.steer, current_cmd.speed);
#endif
/* ROLLBACK-PWM-3-END */

        /* 根据 servo_gear 控制舵机档位 */
        if (current_cmd.servo_gear >= 1 && current_cmd.servo_gear <= 3)
        {
          Servo_SetGear(current_cmd.servo_gear);
        }

        last_cmd_tick = HAL_GetTick();

        /* 立即发送反馈帧给 NUC */
        send_feedback(&current_cmd);
        last_feedback_tick = HAL_GetTick();

        /* PC13 闪一下表示收到有效命令 */
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
        HAL_Delay(50);
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
      }
      else
      {
        /* 解析失败，打印错误类型 */
        debug_print(result == 1 ? "[FAIL] Bad header\r\n" : "[FAIL] Bad checksum\r\n");
      }
    }
    else
    {
      /* 超时无数据：如果超过 1 秒没收到命令，安全回到停止位置。 */
/* ROLLBACK-PWM-4-BEGIN (使用新模块) */
#if 0
      if ((HAL_GetTick() - last_cmd_tick) > 1000) {
        ESC_PWM_Stop();
      }
#endif
/* ROLLBACK-PWM-4-END */
    }

    /* 周期性发送反馈帧：每 200ms 发送一次，保持 NUC 驱动 "connected" 状态 */
    /* 驱动 1s 收不到反馈会判定离线 */
    if ((HAL_GetTick() - last_feedback_tick) >= FEEDBACK_PERIOD_MS)
    {
      send_feedback(&current_cmd);
      last_feedback_tick = HAL_GetTick();
    }
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */

  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Supply configuration update enable
  */
  HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);

  /** Configure the main internal regulator output voltage
  */
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

  while(!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {}

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM = 2;
  RCC_OscInitStruct.PLL.PLLN = 16;
  RCC_OscInitStruct.PLL.PLLP = 1;
  RCC_OscInitStruct.PLL.PLLQ = 2;
  RCC_OscInitStruct.PLL.PLLR = 2;
  RCC_OscInitStruct.PLL.PLLRGE = RCC_PLL1VCIRANGE_3;
  RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
  RCC_OscInitStruct.PLL.PLLFRACN = 0;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2
                              |RCC_CLOCKTYPE_D3PCLK1|RCC_CLOCKTYPE_D1PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV2;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;
  RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV2;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

 /* MPU Configuration */

void MPU_Config(void)
{
  MPU_Region_InitTypeDef MPU_InitStruct = {0};

  /* Disables the MPU */
  HAL_MPU_Disable();

  /** Initializes and configures the Region and the memory to be protected
  */
  MPU_InitStruct.Enable = MPU_REGION_ENABLE;
  MPU_InitStruct.Number = MPU_REGION_NUMBER0;
  MPU_InitStruct.BaseAddress = 0x0;
  MPU_InitStruct.Size = MPU_REGION_SIZE_4GB;
  MPU_InitStruct.SubRegionDisable = 0x87;
  MPU_InitStruct.TypeExtField = MPU_TEX_LEVEL0;
  MPU_InitStruct.AccessPermission = MPU_REGION_NO_ACCESS;
  MPU_InitStruct.DisableExec = MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU_InitStruct.IsShareable = MPU_ACCESS_SHAREABLE;
  MPU_InitStruct.IsCacheable = MPU_ACCESS_NOT_CACHEABLE;
  MPU_InitStruct.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;

  HAL_MPU_ConfigRegion(&MPU_InitStruct);
  /* Enables the MPU */
  HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);

}

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
