/**
 ******************************************************************************
 * @file    servo_controller.c
 * @brief   MG996R 舵机控制模块实现
 ******************************************************************************
 */

#include "servo_controller.h"
#include "tim.h"
#include "main.h"

/* ====== 硬件配置 ====== */
#define SERVO_HTIM           htim2         /* TIM2: 50Hz (PSC=191, ARR=19999) */
#define SERVO_TIM_CH         TIM_CHANNEL_1 /* CH1 → PA00 */

/* ====== MG996R 180° 舵机脉宽参数 (1 count = 1μs) ====== */
#define SERVO_PULSE_MIN      500U   /* 0.5ms → 0° */
#define SERVO_PULSE_MID      1500U  /* 1.5ms → 90° (中位) */
#define SERVO_PULSE_MAX      2500U  /* 2.5ms → 180° */

/* ====== 安全角度范围：留机械余量，避免顶死 ====== */
#define SERVO_ANGLE_SAFE_MIN 20     /* 最小 20° */
#define SERVO_ANGLE_SAFE_MAX 160    /* 最大 160° */
#define SERVO_ANGLE_MID      90     /* 中位 90° */

/* ====== 私有变量 ====== */
static uint8_t current_angle = SERVO_ANGLE_MID;  /* 当前角度 */
static bool is_initialized = false;              /* 初始化标志 */

/* ====== 私有函数 ====== */

/**
 * @brief 角度转 PWM 脉宽值
 * @param angle 角度 (0~180°)
 * @retval PWM CCR 值 (500~2500)
 */
static uint16_t angle_to_pulse(uint8_t angle)
{
    /* 限幅到 0~180° */
    if (angle > 180) angle = 180;
    
    /* 线性映射：0° → 500us, 180° → 2500us */
    return SERVO_PULSE_MIN + (angle * (SERVO_PULSE_MAX - SERVO_PULSE_MIN) / 180);
}

/**
 * @brief 应用 PWM 脉宽到硬件
 * @param pulse PWM CCR 值
 */
static void apply_pwm(uint16_t pulse)
{
    __HAL_TIM_SET_COMPARE(&SERVO_HTIM, SERVO_TIM_CH, pulse);
}

/* ====== 公共函数实现 ====== */

int Servo_Init(void)
{
    if (is_initialized) {
        return 0;  /* 避免重复初始化 */
    }
    
    /* 启动 PWM 输出 */
    if (HAL_TIM_PWM_Start(&SERVO_HTIM, SERVO_TIM_CH) != HAL_OK) {
        return -1;
    }
    
    /* 复位到中位 */
    current_angle = SERVO_ANGLE_MID;
    apply_pwm(angle_to_pulse(current_angle));
    
    is_initialized = true;
    return 0;
}

uint8_t Servo_SetAngle(uint8_t angle)
{
    /* 安全限幅 */
    if (angle < SERVO_ANGLE_SAFE_MIN) {
        angle = SERVO_ANGLE_SAFE_MIN;
    } else if (angle > SERVO_ANGLE_SAFE_MAX) {
        angle = SERVO_ANGLE_SAFE_MAX;
    }
    
    /* 应用 PWM */
    uint16_t pulse = angle_to_pulse(angle);
    apply_pwm(pulse);
    
    /* 更新状态 */
    current_angle = angle;
    return angle;
}

uint8_t Servo_GetAngle(void)
{
    return current_angle;
}

void Servo_Reset(void)
{
    Servo_SetAngle(SERVO_ANGLE_MID);
}

void Servo_TestSequence(void (*led_callback)(uint8_t stage))
{
    const uint8_t test_angles[] = {0, 45, 90, 135, 180, 90};
    const uint16_t stage_delay_ms = 800;
    
    for (uint8_t i = 0; i < 6; i++) {
        /* 设置角度 */
        Servo_SetAngle(test_angles[i]);
        
        /* LED 指示（可选） */
        if (led_callback != NULL) {
            led_callback(i + 1);
        }
        
        /* 等待舵机到位 */
        HAL_Delay(stage_delay_ms);
    }
}
