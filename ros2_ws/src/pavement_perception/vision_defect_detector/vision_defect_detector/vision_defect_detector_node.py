#!/usr/bin/env python3
"""
视觉表观缺陷检测节点 - 基于 YOLO11 .pt

定位：输出“表观异常/疑似缺陷”候选，不直接给出结构安全结论。
订阅: /camera/image_raw (sensor_msgs/Image)
发布: /perception/vision_defects (pavement_interfaces/DefectArray)
发布: /perception/detection_image (sensor_msgs/Image) - 可视化图像
"""

import json
from pathlib import Path

import cv2
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Point, Vector3
from rclpy.node import Node
from sensor_msgs.msg import Image
from pavement_interfaces.msg import DefectArray, DefectInfo

try:
    from ultralytics import YOLO
except Exception:  # noqa: BLE001
    YOLO = None


class VisionDefectDetectorNode(Node):
    def __init__(self):
        super().__init__('vision_defect_detector_node')

        self.declare_parameter(
            'model_path',
            '/home/qyb413/CyberLuban/campusCar/vision_models/models/campus_road_best.pt',
        )
        self.declare_parameter('confidence_threshold', 0.40)
        self.declare_parameter('input_size', 960)
        self.declare_parameter('device', 'cpu')
        self.declare_parameter('enable_visualization', True)
        self.declare_parameter('defect_id_prefix', 'vision')
        self.declare_parameter('image_topic', '/camera/image_raw')

        self.model_path = self.get_parameter('model_path').value
        self.confidence_threshold = float(self.get_parameter('confidence_threshold').value)
        self.input_size = int(self.get_parameter('input_size').value)
        self.device = self.get_parameter('device').value
        self.enable_visualization = bool(self.get_parameter('enable_visualization').value)
        self.defect_id_prefix = self.get_parameter('defect_id_prefix').value
        self.image_topic = self.get_parameter('image_topic').value

        self.bridge = CvBridge()
        self.defect_counter = 0
        self.model = self.load_model()

        self.image_sub = self.create_subscription(Image, self.image_topic, self.image_callback, 10)
        self.defect_pub = self.create_publisher(DefectArray, '/perception/vision_defects', 10)
        self.vis_pub = self.create_publisher(Image, '/perception/detection_image', 10)

        self.get_logger().info('=' * 70)
        self.get_logger().info('YOLO11 视觉表观缺陷检测节点已启动')
        self.get_logger().info(f'  订阅图像: {self.image_topic}')
        self.get_logger().info(f'  模型: {self.model_path}')
        self.get_logger().info(f'  输入尺寸: {self.input_size}')
        self.get_logger().info(f'  置信度阈值: {self.confidence_threshold}')
        self.get_logger().info(f'  推理设备: {self.device}')
        self.get_logger().info('  发布: /perception/vision_defects, /perception/detection_image')
        self.get_logger().info('  注意: 输出为视觉表观缺陷候选，非结构安全结论')
        self.get_logger().info('=' * 70)

    def load_model(self):
        if YOLO is None:
            self.get_logger().error('未安装 ultralytics，无法加载 YOLO11 .pt 模型')
            self.get_logger().error('安装命令: pip3 install ultralytics')
            return None

        model_path = Path(self.model_path)
        if not model_path.exists():
            self.get_logger().error(f'模型文件不存在: {model_path}')
            return None

        try:
            import torch

            original_torch_load = torch.load

            def torch_load_compat(*args, **kwargs):
                kwargs.setdefault('weights_only', False)
                return original_torch_load(*args, **kwargs)

            torch.load = torch_load_compat
            model = YOLO(str(model_path))
            names = getattr(model, 'names', {})
            self.get_logger().info(f'YOLO 模型加载成功，类别: {names}')
            return model
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'YOLO 模型加载失败: {exc}')
            return None

    def image_callback(self, msg):
        try:
            image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'图像转换失败: {exc}')
            return

        detections = self.detect(image)
        defect_array = self.detections_to_defects(detections, msg.header, image.shape)
        self.defect_pub.publish(defect_array)

        if self.enable_visualization:
            vis_image = self.draw_detections(image, detections)
            vis_msg = self.bridge.cv2_to_imgmsg(vis_image, encoding='bgr8')
            vis_msg.header = msg.header
            self.vis_pub.publish(vis_msg)

        if detections:
            summary = ', '.join(f"{det['class_name']}:{det['confidence']:.2f}" for det in detections[:5])
            self.get_logger().info(f'检测到 {len(detections)} 个表观缺陷候选: {summary}')

    def detect(self, image):
        if self.model is None:
            return []

        try:
            results = self.model.predict(
                source=image,
                imgsz=self.input_size,
                conf=self.confidence_threshold,
                device=self.device,
                verbose=False,
            )
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'YOLO 推理失败: {exc}')
            return []

        detections = []
        if not results:
            return detections

        result = results[0]
        names = getattr(result, 'names', getattr(self.model, 'names', {}))
        boxes = getattr(result, 'boxes', None)
        if boxes is None:
            return detections

        for box in boxes:
            xyxy = box.xyxy[0].detach().cpu().numpy().astype(float)
            conf = float(box.conf[0].detach().cpu().item())
            cls_id = int(box.cls[0].detach().cpu().item())
            class_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
            x1, y1, x2, y2 = xyxy.tolist()
            detections.append({
                'bbox': [int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))],
                'confidence': conf,
                'class_id': cls_id,
                'class_name': class_name,
            })

        return detections

    def detections_to_defects(self, detections, header, image_shape):
        defect_array = DefectArray()
        defect_array.header = header
        image_h, image_w = image_shape[:2]

        for det in detections:
            self.defect_counter += 1
            x1, y1, x2, y2 = det['bbox']
            width_px = max(0, x2 - x1)
            height_px = max(0, y2 - y1)
            pixel_area = width_px * height_px
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0

            defect = DefectInfo()
            defect.header = header
            defect.defect_id = f'{self.defect_id_prefix}_{self.defect_counter:06d}'
            defect.defect_type = det['class_name']
            defect.confidence = float(det['confidence'])
            defect.detection_source = 'vision'
            defect.position = Point(x=float(cx), y=float(cy), z=0.0)
            defect.dimensions = Vector3(x=float(width_px), y=float(height_px), z=0.0)
            defect.severity_level = self.estimate_visual_severity(det['class_name'], det['confidence'], pixel_area, image_w * image_h)
            defect.attributes = json.dumps({
                'interpretation': 'visual_surface_candidate_only',
                'bbox_pixel': [x1, y1, x2, y2],
                'bbox_center_pixel': [cx, cy],
                'pixel_area': pixel_area,
                'image_shape': [image_h, image_w],
                'relative_image_area': pixel_area / max(1, image_w * image_h),
                'model': 'YOLO11n campus_road_best.pt',
                'needs_geometry_confirmation': True,
            }, ensure_ascii=False)
            defect_array.defects.append(defect)

        return defect_array

    def estimate_visual_severity(self, class_name, confidence, pixel_area, image_area):
        area_ratio = pixel_area / max(1, image_area)
        score = 0.5 * float(confidence) + 0.5 * min(1.0, area_ratio / 0.08)
        if class_name in ('pothole', 'rutting', 'depression'):
            score += 0.12
        elif class_name == 'crack':
            score += 0.04

        if score >= 0.80:
            return 'critical'
        if score >= 0.60:
            return 'high'
        if score >= 0.35:
            return 'medium'
        return 'low'

    def draw_detections(self, image, detections):
        vis = image.copy()
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            color = self.class_color(det['class_name'])
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            label = f"{det['class_name']}: {det['confidence']:.2f}"
            cv2.putText(vis, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return vis

    def class_color(self, class_name):
        colors = {
            'pothole': (0, 0, 255),
            'crack': (0, 165, 255),
            'rutting': (0, 255, 255),
            'depression': (255, 0, 255),
        }
        return colors.get(class_name, (0, 255, 0))


def main(args=None):
    rclpy.init(args=args)
    node = VisionDefectDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
