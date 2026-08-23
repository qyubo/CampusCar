#!/usr/bin/env python3
"""
Mock 数据发布器 - 模拟真实相机、雷达、底盘的数据流
用于在没有实际硬件的环境中验证完整工作流程和 ROS2 接口

发布:
  - /livox/pointcloud (sensor_msgs/PointCloud2) - 带合成缺陷的点云
  - /camera/image_raw (sensor_msgs/Image) - 带缺陷标记的彩色图像
  - /camera/camera_info (sensor_msgs/CameraInfo)
  - /odom (nav_msgs/Odometry)
  - /chassis_pose (geometry_msgs/PoseStamped)
  - /tf (tf2_msgs/TFMessage) - 静态/动态变换
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import PointCloud2, PointField, Image, CameraInfo
from geometry_msgs.msg import PoseStamped, TransformStamped, Twist
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage
from std_msgs.msg import Header
import numpy as np
import struct
import math
import random


class MockDataPublisher(Node):
    def __init__(self):
        super().__init__('mock_data_publisher')

        # 参数
        self.declare_parameter('pointcloud_rate', 10.0)
        self.declare_parameter('camera_rate', 10.0)
        self.declare_parameter('odom_rate', 20.0)
        self.declare_parameter('tf_rate', 20.0)
        self.declare_parameter('image_width', 640)
        self.declare_parameter('image_height', 480)
        self.declare_parameter('num_points', 10000)
        self.declare_parameter('enable_defect_synthesis', True)

        pc_rate = self.get_parameter('pointcloud_rate').value
        cam_rate = self.get_parameter('camera_rate').value
        odom_rate = self.get_parameter('odom_rate').value
        tf_rate = self.get_parameter('tf_rate').value
        self.img_w = self.get_parameter('image_width').value
        self.img_h = self.get_parameter('image_height').value
        self.num_points = self.get_parameter('num_points').value
        self.enable_synth_defect = self.get_parameter('enable_defect_synthesis').value

        # 发布者
        self.pc_pub = self.create_publisher(PointCloud2, '/livox/pointcloud', 10)
        self.img_pub = self.create_publisher(Image, '/camera/image_raw', 10)
        self.cam_info_pub = self.create_publisher(CameraInfo, '/camera/camera_info', 10)
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.pose_pub = self.create_publisher(PoseStamped, '/chassis_pose', 10)
        self.tf_pub = self.create_publisher(
            TFMessage, '/tf',
            QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL)
        )
        self.tf_static_pub = self.create_publisher(
            TFMessage, '/tf_static',
            QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL)
        )
        # 订阅 cmd_vel 用于验证 /cmd_vel 链路
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.last_cmd_vel = Twist()

        # 里程计状态
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.linear_vel = 0.3
        self.angular_vel = 0.05
        self.start_time = self.get_clock().now()

        # 定时器
        self.create_timer(1.0 / pc_rate, self.publish_pointcloud)
        self.create_timer(1.0 / cam_rate, self.publish_camera)
        self.create_timer(1.0 / odom_rate, self.publish_odometry)
        self.create_timer(1.0 / tf_rate, self.publish_tf)
        # 静态 TF 只需发布一次（带 transient local durability）
        self.create_timer(0.5, self.publish_static_tf)

        self.frame_cnt = 0
        self.get_logger().info('✅ Mock 数据发布器已启动')
        self.get_logger().info(
            f'   点云: /livox/pointcloud @{pc_rate}Hz ({self.num_points} points/frame)')
        self.get_logger().info(
            f'   图像: /camera/image_raw @{cam_rate}Hz ({self.img_w}x{self.img_h})')
        self.get_logger().info(f'   里程计: /odom @{odom_rate}Hz')
        self.get_logger().info(f'   TF: /tf + /tf_static @{tf_rate}Hz')
        self.get_logger().info(
            f'   (合成缺陷注入: {"已启用" if self.enable_synth_defect else "关闭"})')

    def cmd_vel_callback(self, msg: Twist):
        self.last_cmd_vel = msg
        self.linear_vel = float(msg.linear.x)
        self.angular_vel = float(msg.angular.z)

    # ---------------- PointCloud ----------------
    def publish_pointcloud(self):
        """生成一条平面+若干缺陷点云"""
        N = self.num_points
        pts = np.zeros((N, 4), dtype=np.float32)  # x, y, z, intensity
        rng = np.random.default_rng(self.frame_cnt)
        # 基础路面: x=[-15,15], y=[-10,10], z围绕0有小抖动
        pts[:, 0] = rng.uniform(-15.0, 15.0, N)
        pts[:, 1] = rng.uniform(-10.0, 10.0, N)
        pts[:, 2] = rng.normal(0.0, 0.005, N)  # 路面噪声 5mm
        pts[:, 3] = rng.uniform(0.2, 0.9, N)

        if self.enable_synth_defect:
            # 合成几个缺陷: 一个 pothole (圆形凹陷)、一条crack (长条下凹+上凸)、一小块沉降
            # 1. pothole: 中心 (3, -2), 半径 0.4m, 深度 0.04m
            cx, cy, R, D = 3.0, -2.0, 0.4, 0.04
            d = np.sqrt((pts[:, 0]-cx)**2 + (pts[:, 1]-cy)**2)
            mask = d < R
            pts[mask, 2] -= D * (1 - d[mask]/R)**2

            # 2. 纵向 crack: x=[-5,-1], y≈1, 宽度0.12, 深度0.015m
            mask2 = (pts[:, 0] > -5.0) & (pts[:, 0] < -1.0) & (np.abs(pts[:, 1] - 1.0) < 0.06)
            pts[mask2, 2] -= 0.015

            # 3. 沉降块: 中心 (-3, 4), 半径 1.5m, 深度 0.01m
            cx3, cy3, R3, D3 = -3.0, 4.0, 1.5, 0.01
            d3 = np.sqrt((pts[:, 0]-cx3)**2 + (pts[:, 1]-cy3)**2)
            mask3 = d3 < R3
            pts[mask3, 2] -= D3 * np.cos(np.pi/2 * d3[mask3]/R3)

        fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name='intensity', offset=12, datatype=PointField.FLOAT32, count=1),
        ]
        data = b''.join(struct.pack('ffff', float(p[0]), float(p[1]), float(p[2]), float(p[3])) for p in pts)
        msg = PointCloud2()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'livox_frame'
        msg.height = 1
        msg.width = N
        msg.fields = fields
        msg.is_bigendian = False
        msg.point_step = 16
        msg.row_step = 16 * N
        msg.is_dense = True
        msg.data = data
        self.pc_pub.publish(msg)

    # ---------------- Camera ----------------
    def publish_camera(self):
        """生成一张带人工缺陷纹理的彩色图像（bgr8）"""
        try:
            import cv2
            H, W = self.img_h, self.img_w
            img = np.zeros((H, W, 3), dtype=np.uint8)
            # 灰色路面底
            img[:] = (140, 148, 154)  # BGR
            # 车道线
            img[H//2 - 4:H//2 + 4, ::120, :] = (0, 220, 255)  # 黄虚线
            # 加噪声
            rng = np.random.default_rng(self.frame_cnt)
            noise = rng.integers(-12, 12, (H, W, 3), dtype=np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

            if self.enable_synth_defect:
                # 画 pothole (深色圆)
                cx, cy, r = int(W*0.72), int(H*0.56), int(min(W,H)*0.08)
                cv2.circle(img, (cx, cy), r, (70, 70, 80), -1)
                cv2.circle(img, (cx, cy), r+1, (30, 30, 40), 2)
                # 画 crack (折线)
                pts = np.array([
                    [int(W*0.25), int(H*0.4)],
                    [int(W*0.35), int(H*0.5)],
                    [int(W*0.42), int(H*0.52)],
                    [int(W*0.50), int(H*0.62)],
                ], np.int32).reshape(-1, 1, 2)
                cv2.polylines(img, [pts], False, (50, 50, 55), 3)
                # 沉降区域
                cv2.ellipse(img, (int(W*0.4), int(H*0.75)),
                            (int(W*0.2), int(H*0.07)), 0, 0, 360,
                            (95, 105, 110), -1)
        except Exception:
            # 无 cv2 则纯字节 0
            img = np.zeros((self.img_h, self.img_w, 3), dtype=np.uint8)

        img_msg = Image()
        img_msg.header.stamp = self.get_clock().now().to_msg()
        img_msg.header.frame_id = 'camera_frame'
        img_msg.height = self.img_h
        img_msg.width = self.img_w
        img_msg.encoding = 'bgr8'
        img_msg.is_bigendian = False
        img_msg.step = self.img_w * 3
        img_msg.data = img.tobytes()
        self.img_pub.publish(img_msg)

        # CameraInfo
        info = CameraInfo()
        info.header = img_msg.header
        info.width = self.img_w
        info.height = self.img_h
        info.distortion_model = 'plumb_bob'
        info.k = [float(self.img_w*0.7), 0.0, float(self.img_w*0.5),
                  0.0, float(self.img_w*0.7), float(self.img_h*0.5),
                  0.0, 0.0, 1.0]
        info.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        info.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        fx, fy = info.k[0], info.k[4]
        cx, cy = info.k[2], info.k[5]
        info.p = [fx, 0.0, cx, 0.0, 0.0, fy, cy, 0.0, 0.0, 0.0, 1.0, 0.0]
        self.cam_info_pub.publish(info)

    # ---------------- Odometry ----------------
    def publish_odometry(self):
        now = self.get_clock().now()
        dt = 0.05
        # 让机器人缓慢绕圈
        self.x += self.linear_vel * math.cos(self.theta) * dt
        self.y += self.linear_vel * math.sin(self.theta) * dt
        self.theta += self.angular_vel * dt

        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation.z = float(math.sin(self.theta / 2))
        odom.pose.pose.orientation.w = float(math.cos(self.theta / 2))
        odom.twist.twist.linear.x = self.linear_vel
        odom.twist.twist.angular.z = self.angular_vel
        self.odom_pub.publish(odom)

        ps = PoseStamped()
        ps.header = odom.header
        ps.pose = odom.pose.pose
        self.pose_pub.publish(ps)

    # ---------------- TF ----------------
    def publish_tf(self):
        now = self.get_clock().now().to_msg()
        tfms = TFMessage()
        t1 = TransformStamped()
        t1.header.stamp = now
        t1.header.frame_id = 'odom'
        t1.child_frame_id = 'base_link'
        t1.transform.translation.x = self.x
        t1.transform.translation.y = self.y
        t1.transform.translation.z = 0.0
        t1.transform.rotation.z = float(math.sin(self.theta / 2))
        t1.transform.rotation.w = float(math.cos(self.theta / 2))
        tfms.transforms.append(t1)
        self.tf_pub.publish(tfms)

    def publish_static_tf(self):
        now = self.get_clock().now().to_msg()
        tfms = TFMessage()

        def add_tf(parent, child, xyz, rpy):
            t = TransformStamped()
            t.header.stamp = now
            t.header.frame_id = parent
            t.child_frame_id = child
            t.transform.translation.x = xyz[0]
            t.transform.translation.y = xyz[1]
            t.transform.translation.z = xyz[2]
            cr, sr = math.cos(rpy[0]/2), math.sin(rpy[0]/2)
            cp, sp = math.cos(rpy[1]/2), math.sin(rpy[1]/2)
            cy, sy = math.cos(rpy[2]/2), math.sin(rpy[2]/2)
            t.transform.rotation.w = cr*cp*cy + sr*sp*sy
            t.transform.rotation.x = sr*cp*cy - cr*sp*sy
            t.transform.rotation.y = cr*sp*cy + sr*cp*sy
            t.transform.rotation.z = cr*cp*sy - sr*sp*cy
            tfms.transforms.append(t)

        add_tf('base_link', 'livox_frame', (0.15, 0.0, 0.35), (0.0, 0.0, 0.0))
        add_tf('base_link', 'camera_frame', (0.2, 0.0, 0.30), (0.0, -0.1, 0.0))
        add_tf('base_link', 'imu_link', (0.0, 0.0, 0.1), (0.0, 0.0, 0.0))
        add_tf('map', 'odom', (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        self.tf_static_pub.publish(tfms)
        self.frame_cnt += 1


def main(args=None):
    rclpy.init(args=args)
    node = MockDataPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
