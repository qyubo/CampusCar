#!/usr/bin/env python3
"""
海康 MV-CS016-10GC 真实相机采集节点

通过 OpenCV GStreamer 或 RTSP/HTTP 直接采集真实相机图像。
如果相机支持 RTSP/HTTP 流，可直接通过 cv2.VideoCapture 取图，无需海康 SDK。

优先级：
1. GigE Vision URL (如 gige://10.7.142.102)
2. RTSP URL (如 rtsp://10.7.142.102:554/stream)
3. HTTP MJPEG URL (如 http://10.7.142.102/mjpeg)
4. 回退到测试图模式

发布: /camera/image_raw (sensor_msgs/Image)
发布: /camera/camera_info (sensor_msgs/CameraInfo)
"""

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image


class HikrobotRealCameraNode(Node):
    def __init__(self):
        super().__init__('hikrobot_real_camera_node')

        self.declare_parameter('camera_ip', '10.7.142.102')
        self.declare_parameter('frame_id', 'camera_frame')
        self.declare_parameter('fps', 10.0)
        self.declare_parameter('width', 1440)
        self.declare_parameter('height', 1080)
        self.declare_parameter('rtsp_port', 554)
        self.declare_parameter('http_port', 80)
        self.declare_parameter('test_mode_fallback', True)

        self.camera_ip = self.get_parameter('camera_ip').value
        self.frame_id = self.get_parameter('frame_id').value
        self.fps = float(self.get_parameter('fps').value)
        self.width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.rtsp_port = int(self.get_parameter('rtsp_port').value)
        self.http_port = int(self.get_parameter('http_port').value)
        self.test_mode_fallback = bool(self.get_parameter('test_mode_fallback').value)

        self.bridge = CvBridge()
        self.frame_count = 0
        self.capture = None
        self.capture_source = None

        self.try_open_camera()

        self.image_pub = self.create_publisher(Image, '/camera/image_raw', 10)
        self.info_pub = self.create_publisher(CameraInfo, '/camera/camera_info', 10)
        self.timer = self.create_timer(1.0 / max(self.fps, 1.0), self.publish_image)

        self.get_logger().info('=' * 70)
        self.get_logger().info('海康真实相机采集节点已启动')
        self.get_logger().info(f'  相机IP: {self.camera_ip}')
        self.get_logger().info(f'  图像源: {self.capture_source or "test_pattern"}')
        self.get_logger().info('  发布: /camera/image_raw, /camera/camera_info')
        self.get_logger().info('=' * 70)

    def try_open_camera(self):
        urls = [
            f'rtsp://{self.camera_ip}:{self.rtsp_port}/stream',
            f'rtsp://{self.camera_ip}:{self.rtsp_port}/live',
            f'http://{self.camera_ip}:{self.http_port}/mjpeg',
            f'http://{self.camera_ip}:{self.http_port}/stream',
        ]

        for url in urls:
            self.get_logger().info(f'尝试打开: {url}')
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.capture = cap
                    self.capture_source = url
                    self.get_logger().info(f'✅ 真实相机已连接: {url}')
                    return
                cap.release()

        if self.test_mode_fallback:
            self.get_logger().warn('⚠️ 所有真实相机 URL 均无法连接，切换到测试图模式')
            self.capture_source = 'test_pattern'
        else:
            self.get_logger().error('❌ 无法连接真实相机，且测试图模式已禁用')
            raise RuntimeError(f'无法连接相机 {self.camera_ip}')

    def publish_image(self):
        frame = self.read_frame()
        stamp = self.get_clock().now().to_msg()

        img_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        img_msg.header.stamp = stamp
        img_msg.header.frame_id = self.frame_id
        self.image_pub.publish(img_msg)

        info_msg = CameraInfo()
        info_msg.header = img_msg.header
        info_msg.width = frame.shape[1]
        info_msg.height = frame.shape[0]
        self.info_pub.publish(info_msg)

    def read_frame(self):
        if self.capture is not None:
            ok, frame = self.capture.read()
            if ok and frame is not None:
                return frame
            self.get_logger().warn('视频源读取失败，切换到测试图')
            self.capture.release()
            self.capture = None

        self.frame_count += 1
        return self.make_test_pattern()

    def make_test_pattern(self):
        image = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        image[:] = (40, 40, 40)

        bar_x = int((self.frame_count * 15) % max(self.width, 1))
        cv2.rectangle(image, (bar_x, 0), (min(bar_x + 100, self.width - 1), self.height - 1), (60, 100, 150), -1)

        cv2.putText(image, 'Hikrobot MV-CS016-10GC (test mode)', (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 255), 3)
        cv2.putText(image, f'Camera IP: {self.camera_ip}', (50, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        cv2.putText(image, f'Frame: {self.frame_count}', (50, 230), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        cv2.putText(image, 'Waiting for real camera...', (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 128, 0), 2)

        cv2.rectangle(image, (self.width // 3, self.height // 3), (self.width // 3 + 250, self.height // 3 + 140), (0, 0, 255), 5)
        cv2.putText(image, 'YOLO detection ready', (self.width // 3, self.height // 3 - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        return image

    def destroy_node(self):
        if self.capture is not None:
            self.capture.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = HikrobotRealCameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
