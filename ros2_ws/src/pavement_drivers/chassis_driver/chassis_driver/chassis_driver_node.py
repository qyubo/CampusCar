#!/usr/bin/env python3
"""
底盘驱动节点
- 通过串口与 STM32 通信
- 订阅: /cmd_vel (geometry_msgs/Twist)
- 发布: /odom (nav_msgs/Odometry), /chassis_pose (geometry_msgs/PoseStamped)
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
import serial
import struct
import math


class ChassisDriverNode(Node):
    def __init__(self):
        super().__init__('chassis_driver_node')
        
        # 参数声明
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('wheel_base', 0.5)
        self.declare_parameter('wheel_radius', 0.1)
        self.declare_parameter('max_linear_vel', 1.0)
        self.declare_parameter('max_angular_vel', 1.57)
        
        # 获取参数
        self.serial_port = self.get_parameter('serial_port').value
        self.baud_rate = self.get_parameter('baud_rate').value
        self.wheel_base = self.get_parameter('wheel_base').value
        self.wheel_radius = self.get_parameter('wheel_radius').value
        self.max_linear_vel = self.get_parameter('max_linear_vel').value
        self.max_angular_vel = self.get_parameter('max_angular_vel').value
        
        # 初始化串口（占位，实际需要异常处理）
        try:
            self.serial_conn = serial.Serial(self.serial_port, self.baud_rate, timeout=0.1)
            self.get_logger().info(f'串口已连接: {self.serial_port}')
        except Exception as e:
            self.get_logger().warn(f'串口连接失败: {e}，进入模拟模式')
            self.serial_conn = None
        
        # 订阅速度指令
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        
        # 发布里程计与位姿
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.pose_pub = self.create_publisher(PoseStamped, '/chassis_pose', 10)
        
        # 定时器：读取底盘反馈并发布里程计
        self.timer = self.create_timer(0.05, self.update_odometry)  # 20Hz
        
        # 里程计状态
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_time = self.get_clock().now()
        
        self.get_logger().info('底盘驱动节点已启动')
    
    def cmd_vel_callback(self, msg: Twist):
        """接收速度指令并通过串口下发到底盘"""
        linear_vel = max(-self.max_linear_vel, min(self.max_linear_vel, msg.linear.x))
        angular_vel = max(-self.max_angular_vel, min(self.max_angular_vel, msg.angular.z))
        
        # 差速模型：计算左右轮速度
        left_vel = linear_vel - angular_vel * self.wheel_base / 2.0
        right_vel = linear_vel + angular_vel * self.wheel_base / 2.0
        
        # 封装串口协议（示例：0xAA 0x55 + 左轮速度(float) + 右轮速度(float) + 校验和）
        if self.serial_conn:
            try:
                packet = struct.pack('<BBffB', 0xAA, 0x55, left_vel, right_vel, 0x00)
                self.serial_conn.write(packet)
            except Exception as e:
                self.get_logger().error(f'串口写入失败: {e}')
    
    def update_odometry(self):
        """读取底盘反馈，更新并发布里程计"""
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9
        self.last_time = current_time
        
        # TODO: 从串口读取实际里程计数据（此处为占位模拟）
        # 实际应该解析STM32返回的编码器数据
        linear_vel = 0.0  # 模拟值
        angular_vel = 0.0  # 模拟值
        
        # 更新位姿
        delta_x = linear_vel * math.cos(self.theta) * dt
        delta_y = linear_vel * math.sin(self.theta) * dt
        delta_theta = angular_vel * dt
        
        self.x += delta_x
        self.y += delta_y
        self.theta += delta_theta
        
        # 发布 Odometry
        odom_msg = Odometry()
        odom_msg.header.stamp = current_time.to_msg()
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = 'base_link'
        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.orientation.z = math.sin(self.theta / 2.0)
        odom_msg.pose.pose.orientation.w = math.cos(self.theta / 2.0)
        odom_msg.twist.twist.linear.x = linear_vel
        odom_msg.twist.twist.angular.z = angular_vel
        self.odom_pub.publish(odom_msg)
        
        # 发布 PoseStamped
        pose_msg = PoseStamped()
        pose_msg.header = odom_msg.header
        pose_msg.pose = odom_msg.pose.pose
        self.pose_pub.publish(pose_msg)


def main(args=None):
    rclpy.init(args=args)
    node = ChassisDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
