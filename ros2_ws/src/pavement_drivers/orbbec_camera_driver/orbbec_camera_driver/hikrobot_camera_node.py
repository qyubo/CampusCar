#!/usr/bin/env python3
"""海康工业相机 ROS2 图像输入节点。

后端优先级由 ``backend`` 控制：

* ``auto``：无 ``source`` 时优先尝试 MVS，失败后发布诊断测试图；
* ``mvs``：使用海康 MVS Python SDK，SDK 或相机不可用时节点退出；
* ``opencv``：从 OpenCV 支持的视频源读取；
* ``test``：发布动态测试图，用于先验证 ROS/YOLO 链路。

发布：``/camera/image_raw``、``/camera/camera_info``。
"""

from pathlib import Path

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image

from .mvs_camera import MvsCamera, MvsCameraError


class HikrobotCameraNode(Node):
    def __init__(self) -> None:
        super().__init__('hikrobot_camera_node')

        self.declare_parameter('backend', 'auto')
        self.declare_parameter('camera_ip', '10.7.142.102')
        self.declare_parameter('serial_number', '')
        self.declare_parameter('mvs_python_path', '')
        self.declare_parameter('frame_id', 'camera_frame')
        self.declare_parameter('fps', 10.0)
        self.declare_parameter('source', '')
        self.declare_parameter('width', 1440)
        self.declare_parameter('height', 1080)
        self.declare_parameter('grab_timeout_ms', 1000)

        self.backend_requested = str(self.get_parameter('backend').value).strip().lower()
        self.camera_ip = str(self.get_parameter('camera_ip').value).strip()
        self.serial_number = str(self.get_parameter('serial_number').value).strip()
        self.mvs_python_path = str(self.get_parameter('mvs_python_path').value).strip()
        self.frame_id = str(self.get_parameter('frame_id').value)
        self.fps = float(self.get_parameter('fps').value)
        self.source = str(self.get_parameter('source').value).strip()
        self.width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.grab_timeout_ms = int(self.get_parameter('grab_timeout_ms').value)

        if self.backend_requested not in {'auto', 'mvs', 'opencv', 'test'}:
            raise ValueError('backend 必须是 auto、mvs、opencv 或 test')
        if self.backend_requested == 'opencv' and not self.source:
            raise ValueError('backend=opencv 时必须设置 source')

        self.bridge = CvBridge()
        self.capture = None
        self.mvs_camera = None
        self.backend = 'test'
        self.frame_count = 0
        self.last_error = ''
        self._open_backend()

        self.image_pub = self.create_publisher(Image, '/camera/image_raw', 10)
        self.info_pub = self.create_publisher(CameraInfo, '/camera/camera_info', 10)
        self.timer = self.create_timer(1.0 / max(self.fps, 1.0), self.publish_image)

        self.get_logger().info('=' * 70)
        self.get_logger().info('海康相机图像输入节点已启动')
        self.get_logger().info(f'  请求后端: {self.backend_requested}')
        self.get_logger().info(f'  实际后端: {self.backend}')
        self.get_logger().info(f'  相机IP: {self.camera_ip or "<auto>"}')
        self.get_logger().info(f'  发布: /camera/image_raw, /camera/camera_info')
        if self.backend == 'test':
            self.get_logger().warn('当前发布诊断测试图，不代表已取得真实相机画面')
        self.get_logger().info('=' * 70)

    def _open_backend(self) -> None:
        if self.backend_requested in {'auto', 'mvs'} and not self.source:
            try:
                self.mvs_camera = MvsCamera(
                    camera_ip=self.camera_ip,
                    serial_number=self.serial_number,
                    sdk_path=self.mvs_python_path,
                    width=self.width,
                    height=self.height,
                    fps=self.fps,
                    timeout_ms=self.grab_timeout_ms,
                )
                self.backend = 'mvs'
                self.get_logger().info('MVS SDK 相机打开成功')
                return
            except MvsCameraError as exc:
                self.last_error = str(exc)
                if self.backend_requested == 'mvs':
                    raise RuntimeError(self.last_error) from exc
                self.get_logger().warn(f'MVS 后端不可用，继续尝试其他后端: {exc}')

        if self.backend_requested in {'auto', 'opencv'} and self.source:
            self.capture = self._open_capture(self.source)
            if self.capture is not None:
                self.backend = 'opencv'
                return
            if self.backend_requested == 'opencv':
                raise RuntimeError(f'OpenCV 视频源打开失败: {self.source}')

        if self.backend_requested == 'mvs':
            raise RuntimeError('backend=mvs 时不能设置 source')
        self.backend = 'test'

    def _open_capture(self, source: str):
        source_value = int(source) if source.isdigit() else str(Path(source).expanduser())
        capture = cv2.VideoCapture(source_value)
        if not capture.isOpened():
            capture.release()
            return None
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        capture.set(cv2.CAP_PROP_FPS, self.fps)
        self.get_logger().info(f'OpenCV 视频源打开成功: {source}')
        return capture

    def publish_image(self) -> None:
        frame = self.read_frame()
        stamp = self.get_clock().now().to_msg()

        image_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        image_msg.header.stamp = stamp
        image_msg.header.frame_id = self.frame_id
        self.image_pub.publish(image_msg)

        info_msg = CameraInfo()
        info_msg.header = image_msg.header
        info_msg.width = frame.shape[1]
        info_msg.height = frame.shape[0]
        self.info_pub.publish(info_msg)

    def read_frame(self) -> np.ndarray:
        if self.backend == 'mvs':
            try:
                return self.mvs_camera.read()
            except MvsCameraError as exc:
                self._warn_once(str(exc))
                return self.make_test_pattern('MVS frame unavailable')

        if self.backend == 'opencv':
            ok, frame = self.capture.read()
            if ok and frame is not None:
                return frame
            self._warn_once(f'OpenCV 视频源读取失败: {self.source}')
            return self.make_test_pattern('OpenCV frame unavailable')

        return self.make_test_pattern('test backend')

    def _warn_once(self, message: str) -> None:
        if message != self.last_error:
            self.last_error = message
            self.get_logger().warn(message)

    def make_test_pattern(self, status: str) -> np.ndarray:
        self.frame_count += 1
        image = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        image[:] = (35, 35, 35)

        bar_x = int((self.frame_count * 12) % max(self.width, 1))
        cv2.rectangle(
            image,
            (bar_x, 0),
            (min(bar_x + 80, self.width - 1), self.height - 1),
            (50, 80, 130),
            -1,
        )
        cv2.putText(
            image,
            'Hikrobot camera input diagnostic',
            (40, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 255),
            3,
        )
        cv2.putText(
            image,
            f'/camera/image_raw frame={self.frame_count}',
            (40, 140),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            image,
            f'{status} ip={self.camera_ip}',
            (40, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 165, 255),
            2,
        )
        cv2.rectangle(
            image,
            (self.width // 3, self.height // 3),
            (self.width // 3 + 220, self.height // 3 + 120),
            (0, 0, 255),
            4,
        )
        cv2.putText(
            image,
            'ROS image topic alive',
            (self.width // 3, self.height // 3 - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2,
        )
        return image

    def destroy_node(self) -> None:
        if self.capture is not None:
            self.capture.release()
        if self.mvs_camera is not None:
            self.mvs_camera.close()
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = HikrobotCameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
