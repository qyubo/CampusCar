#!/usr/bin/env python3
"""奥比中光 RGBD 相机 ROS2 输入节点。"""

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image

try:
    from pyorbbecsdk import Config, OBError, OBFormat, OBSensorType, Pipeline
except Exception:  # SDK 未安装时在节点启动阶段给出清晰错误
    Config = None
    OBError = Exception
    OBFormat = None
    OBSensorType = None
    Pipeline = None


class OrbbecCameraNode(Node):
    def __init__(self) -> None:
        super().__init__('orbbec_camera_node')

        self.declare_parameter('frame_id', 'orbbec_color_frame')
        self.declare_parameter('depth_frame_id', 'orbbec_depth_frame')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 30)
        self.declare_parameter('timeout_ms', 1000)
        self.declare_parameter('enable_color', True)
        self.declare_parameter('enable_depth', True)

        self.frame_id = str(self.get_parameter('frame_id').value)
        self.depth_frame_id = str(self.get_parameter('depth_frame_id').value)
        self.width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.fps = int(self.get_parameter('fps').value)
        self.timeout_ms = int(self.get_parameter('timeout_ms').value)
        self.enable_color = bool(self.get_parameter('enable_color').value)
        self.enable_depth = bool(self.get_parameter('enable_depth').value)

        if Pipeline is None:
            raise RuntimeError('未安装 pyorbbecsdk，请先安装 Orbbec SDK Python 绑定和 udev 规则')
        if not self.enable_color and not self.enable_depth:
            raise ValueError('enable_color 和 enable_depth 至少启用一个')

        self.bridge = CvBridge()
        self.pipeline = Pipeline()
        self.config = Config()
        self.last_error = ''

        self._configure_streams()
        self.pipeline.start(self.config)

        self.color_pub = self.create_publisher(Image, '/camera/color/image_raw', 10)
        self.depth_pub = self.create_publisher(Image, '/camera/depth/image_raw', 10)
        self.color_info_pub = self.create_publisher(CameraInfo, '/camera/color/camera_info', 10)
        self.depth_info_pub = self.create_publisher(CameraInfo, '/camera/depth/camera_info', 10)
        self.timer = self.create_timer(1.0 / max(float(self.fps), 1.0), self.publish_frames)

        self.get_logger().info('=' * 70)
        self.get_logger().info('奥比中光 RGBD 相机节点已启动')
        self.get_logger().info(f'  color: {self.enable_color} -> /camera/color/image_raw')
        self.get_logger().info(f'  depth: {self.enable_depth} -> /camera/depth/image_raw')
        self.get_logger().info(f'  profile: {self.width}x{self.height}@{self.fps}')
        self.get_logger().info('=' * 70)

    def _configure_streams(self) -> None:
        if self.enable_color:
            color_profile = self._select_profile(OBSensorType.COLOR_SENSOR, OBFormat.RGB)
            self.config.enable_stream(color_profile)
            self.get_logger().info(f'启用彩色流: {color_profile}')

        if self.enable_depth:
            depth_profile = self._select_profile(OBSensorType.DEPTH_SENSOR, OBFormat.Y16)
            self.config.enable_stream(depth_profile)
            self.get_logger().info(f'启用深度流: {depth_profile}')

    def _select_profile(self, sensor_type, preferred_format):
        profile_list = self.pipeline.get_stream_profile_list(sensor_type)
        try:
            return profile_list.get_video_stream_profile(
                self.width,
                self.height,
                preferred_format,
                self.fps,
            )
        except Exception as exc:
            self.get_logger().warn(f'指定分辨率不可用，使用默认 profile: {exc}')
            return profile_list.get_default_video_stream_profile()

    def publish_frames(self) -> None:
        try:
            frames = self.pipeline.wait_for_frames(self.timeout_ms)
        except OBError as exc:
            self._warn_once(f'Orbbec 取帧失败: {exc}')
            return

        if frames is None:
            self._warn_once('Orbbec 等待帧超时')
            return

        stamp = self.get_clock().now().to_msg()

        if self.enable_color:
            color_frame = frames.get_color_frame()
            if color_frame is not None:
                color_image = self._color_frame_to_bgr(color_frame)
                if color_image is not None:
                    msg = self.bridge.cv2_to_imgmsg(color_image, encoding='bgr8')
                    msg.header.stamp = stamp
                    msg.header.frame_id = self.frame_id
                    self.color_pub.publish(msg)
                    self.color_info_pub.publish(self._camera_info(msg.header, color_image.shape[1], color_image.shape[0]))

        if self.enable_depth:
            depth_frame = frames.get_depth_frame()
            if depth_frame is not None:
                depth_image = self._depth_frame_to_uint16(depth_frame)
                if depth_image is not None:
                    msg = self.bridge.cv2_to_imgmsg(depth_image, encoding='16UC1')
                    msg.header.stamp = stamp
                    msg.header.frame_id = self.depth_frame_id
                    self.depth_pub.publish(msg)
                    self.depth_info_pub.publish(self._camera_info(msg.header, depth_image.shape[1], depth_image.shape[0]))

    def _color_frame_to_bgr(self, frame):
        width = frame.get_width()
        height = frame.get_height()
        data = np.frombuffer(frame.get_data(), dtype=np.uint8)
        frame_format = frame.get_format()

        if frame_format == OBFormat.RGB:
            rgb = data.reshape((height, width, 3))
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        if frame_format == OBFormat.BGR:
            return data.reshape((height, width, 3))
        if frame_format == OBFormat.MJPG:
            return cv2.imdecode(data, cv2.IMREAD_COLOR)
        if frame_format == OBFormat.YUYV:
            yuyv = data.reshape((height, width, 2))
            return cv2.cvtColor(yuyv, cv2.COLOR_YUV2BGR_YUY2)

        self._warn_once(f'暂不支持的 Orbbec 彩色格式: {frame_format}')
        return None

    def _depth_frame_to_uint16(self, frame):
        width = frame.get_width()
        height = frame.get_height()
        data = np.frombuffer(frame.get_data(), dtype=np.uint16).reshape((height, width))
        scale = frame.get_depth_scale() if hasattr(frame, 'get_depth_scale') else 1.0
        if scale != 1.0:
            data = np.clip(data.astype(np.float32) * scale, 0, np.iinfo(np.uint16).max).astype(np.uint16)
        return data

    def _camera_info(self, header, width: int, height: int) -> CameraInfo:
        info = CameraInfo()
        info.header = header
        info.width = width
        info.height = height
        return info

    def _warn_once(self, message: str) -> None:
        if message != self.last_error:
            self.last_error = message
            self.get_logger().warn(message)

    def destroy_node(self) -> None:
        try:
            self.pipeline.stop()
        except Exception:
            pass
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = OrbbecCameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
