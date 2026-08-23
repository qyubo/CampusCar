#!/usr/bin/env python3
"""
舵机视觉反馈控制节点
功能：根据相机画面中目标的垂直位置，自动调整舵机俯仰角度
原理：目标在画面上方 → 舵机抬高；目标在画面下方 → 舵机降低
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from std_msgs.msg import UInt8
import cv2
import numpy as np
from cv_bridge import CvBridge
import struct

class ServoVisionController(Node):
    def __init__(self):
        super().__init__('servo_vision_controller')
        
        # ========== 参数配置 ==========
        self.declare_parameter('image_topic', '/hikrobot_camera/image_raw')
        self.declare_parameter('image_compressed', False)
        self.declare_parameter('servo_control_mode', 'target_tracking')  # 'target_tracking' or 'manual'
        self.declare_parameter('target_y_ratio', 0.5)  # 目标在画面中的期望位置（0.5=中心）
        self.declare_parameter('kp', 0.3)  # PID比例系数
        self.declare_parameter('min_angle', 20)
        self.declare_parameter('max_angle', 160)
        self.declare_parameter('default_angle', 90)
        
        # 串口通信参数
        self.declare_parameter('stm32_device', '/dev/ttyUSB0')  # 根据实际情况修改
        self.declare_parameter('baud_rate', 115200)
        
        # 读取参数
        self.image_topic = self.get_parameter('image_topic').value
        self.image_compressed = self.get_parameter('image_compressed').value
        self.control_mode = self.get_parameter('servo_control_mode').value
        self.target_y_ratio = self.get_parameter('target_y_ratio').value
        self.kp = self.get_parameter('kp').value
        self.min_angle = self.get_parameter('min_angle').value
        self.max_angle = self.get_parameter('max_angle').value
        
        # 状态变量
        self.current_angle = self.get_parameter('default_angle').value
        self.bridge = CvBridge()
        self.frame_count = 0
        
        # 串口连接
        self.serial_port = None
        self.setup_serial()
        
        # 订阅相机图像
        if self.image_compressed:
            self.image_sub = self.create_subscription(
                CompressedImage,
                self.image_topic,
                self.compressed_image_callback,
                10
            )
        else:
            self.image_sub = self.create_subscription(
                Image,
                self.image_topic,
                self.image_callback,
                10
            )
        
        # 发布调试信息
        self.servo_angle_pub = self.create_publisher(UInt8, '/servo_angle', 10)
        
        self.get_logger().info(f'舵机视觉控制节点已启动')
        self.get_logger().info(f'  - 图像话题: {self.image_topic}')
        self.get_logger().info(f'  - 控制模式: {self.control_mode}')
        self.get_logger().info(f'  - 角度范围: {self.min_angle}° ~ {self.max_angle}°')
    
    def setup_serial(self):
        """初始化串口连接"""
        try:
            import serial
            device = self.get_parameter('stm32_device').value
            baud = self.get_parameter('baud_rate').value
            self.serial_port = serial.Serial(device, baud, timeout=0.1)
            self.get_logger().info(f'串口已连接: {device} @ {baud}')
        except Exception as e:
            self.get_logger().error(f'串口连接失败: {e}')
            self.serial_port = None
    
    def send_command(self, steer=0, speed=0, servo_angle=90):
        """
        发送控制命令到STM32
        协议格式（10字节）:
        [0-1] start: 0xABCD (小端)
        [2-3] steer: int16 (-1000~1000)
        [4-5] speed: int16 (-1000~1000)
        [6]   servo_angle: uint8 (0~180)
        [7]   reserved: 0x00
        [8-9] checksum: uint16 (XOR校验)
        """
        if self.serial_port is None:
            return
        
        # 限幅
        steer = max(-1000, min(1000, int(steer)))
        speed = max(-1000, min(1000, int(speed)))
        servo_angle = max(0, min(180, int(servo_angle)))
        
        # 构建数据包
        start = 0xABCD
        reserved = 0x00
        
        # 小端序打包
        data = struct.pack('<Hhhbb', start, steer, speed, servo_angle, reserved)
        
        # 计算校验和 (XOR)
        checksum = start ^ (steer & 0xFFFF) ^ (speed & 0xFFFF) ^ servo_angle ^ reserved
        data += struct.pack('<H', checksum)
        
        try:
            self.serial_port.write(data)
            self.get_logger().debug(f'发送命令: steer={steer}, speed={speed}, servo={servo_angle}°')
        except Exception as e:
            self.get_logger().error(f'串口发送失败: {e}')
    
    def image_callback(self, msg):
        """原始图像回调"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            self.process_image(cv_image)
        except Exception as e:
            self.get_logger().error(f'图像转换失败: {e}')
    
    def compressed_image_callback(self, msg):
        """压缩图像回调"""
        try:
            np_arr = np.frombuffer(msg.data, np.uint8)
            cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            self.process_image(cv_image)
        except Exception as e:
            self.get_logger().error(f'压缩图像解码失败: {e}')
    
    def process_image(self, image):
        """
        图像处理与舵机控制逻辑
        这里实现简单的目标检测（示例：检测红色物体）
        你可以替换为YOLO、OpenCV等任意算法
        """
        self.frame_count += 1
        
        # 每5帧处理一次（降低CPU负载）
        if self.frame_count % 5 != 0:
            return
        
        height, width = image.shape[:2]
        
        if self.control_mode == 'target_tracking':
            # ========== 示例：检测红色物体 ==========
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # 红色HSV范围（可调整）
            lower_red1 = np.array([0, 100, 100])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([160, 100, 100])
            upper_red2 = np.array([180, 255, 255])
            
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask = cv2.bitwise_or(mask1, mask2)
            
            # 查找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if len(contours) > 0:
                # 找到最大轮廓
                largest_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(largest_contour)
                
                # 面积阈值过滤噪点
                if area > 500:
                    # 获取目标中心点
                    M = cv2.moments(largest_contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        
                        # 计算目标在画面中的垂直位置比例 (0=顶部, 1=底部)
                        y_ratio = cy / height
                        
                        # 计算误差
                        error = self.target_y_ratio - y_ratio
                        
                        # PID控制（简化版，仅P）
                        angle_adjustment = error * self.kp * (self.max_angle - self.min_angle)
                        new_angle = self.current_angle + angle_adjustment
                        
                        # 限幅
                        new_angle = max(self.min_angle, min(self.max_angle, new_angle))
                        self.current_angle = new_angle
                        
                        self.get_logger().info(
                            f'目标位置: ({cx}, {cy}), y_ratio={y_ratio:.2f}, '
                            f'误差={error:.2f}, 舵机角度={self.current_angle:.1f}°'
                        )
            else:
                # 未检测到目标，保持当前角度或回中
                self.get_logger().debug('未检测到目标')
        
        # 发送舵机命令
        self.send_command(steer=0, speed=0, servo_angle=int(self.current_angle))
        
        # 发布当前角度
        angle_msg = UInt8()
        angle_msg.data = int(self.current_angle)
        self.servo_angle_pub.publish(angle_msg)

def main(args=None):
    rclpy.init(args=args)
    node = ServoVisionController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
