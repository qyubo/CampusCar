#!/usr/bin/env python3
"""
多传感器融合节点 - 激光+视觉融合
订阅: /perception/lidar_defects (pavement_interfaces/DefectArray)
订阅: /perception/vision_defects (pavement_interfaces/DefectArray)
订阅: /camera/camera_info (sensor_msgs/CameraInfo)
发布: /perception/fused_defects (pavement_interfaces/DefectArray)
"""
import rclpy
from rclpy.node import Node
from pavement_interfaces.msg import DefectArray, DefectInfo
from sensor_msgs.msg import CameraInfo
from geometry_msgs.msg import Point, Vector3
import numpy as np
from message_filters import ApproximateTimeSynchronizer, Subscriber
import json


class SensorFusionNode(Node):
    def __init__(self):
        super().__init__('sensor_fusion_node')
        
        # 参数声明
        self.declare_parameter('lidar_to_camera_tf', [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # x,y,z,roll,pitch,yaw
        self.declare_parameter('matching_distance_threshold', 1.0)  # 空间匹配阈值(米)
        self.declare_parameter('confidence_boost_factor', 1.5)  # 双重检出置信度提升
        self.declare_parameter('confidence_penalty_factor', 0.7)  # 单一检出置信度惩罚
        self.declare_parameter('min_fused_confidence', 0.4)
        self.declare_parameter('time_sync_slop', 0.1)  # 时间同步容忍度(秒)
        
        # 获取参数
        tf_params = self.get_parameter('lidar_to_camera_tf').value
        self.matching_dist = self.get_parameter('matching_distance_threshold').value
        self.conf_boost = self.get_parameter('confidence_boost_factor').value
        self.conf_penalty = self.get_parameter('confidence_penalty_factor').value
        self.min_conf = self.get_parameter('min_fused_confidence').value
        sync_slop = self.get_parameter('time_sync_slop').value
        
        # 构建外参变换矩阵（激光到相机）
        self.T_lidar_to_camera = self.build_transform_matrix(tf_params)
        
        # 相机内参
        self.camera_matrix = None
        self.dist_coeffs = None
        self.image_size = (1920, 1080)  # 默认值
        
        # 订阅相机内参
        self.camera_info_sub = self.create_subscription(
            CameraInfo, '/camera/camera_info', self.camera_info_callback, 10)
        
        # 时间同步订阅激光和视觉缺陷
        self.lidar_sub = Subscriber(self, DefectArray, '/perception/lidar_defects')
        self.vision_sub = Subscriber(self, DefectArray, '/perception/vision_defects')
        
        self.sync = ApproximateTimeSynchronizer(
            [self.lidar_sub, self.vision_sub],
            queue_size=10,
            slop=sync_slop
        )
        self.sync.registerCallback(self.fusion_callback)
        
        # 发布融合结果
        self.fused_pub = self.create_publisher(DefectArray, '/perception/fused_defects', 10)
        
        self.fusion_counter = 0
        
        self.get_logger().info('多传感器融合节点已启动')
        self.get_logger().info(f'匹配阈值: {self.matching_dist}m, 时间同步容忍: {sync_slop}s')
    
    def build_transform_matrix(self, params):
        """构建4x4变换矩阵"""
        x, y, z, roll, pitch, yaw = params
        
        # 旋转矩阵（ZYX欧拉角）
        cr = np.cos(roll)
        sr = np.sin(roll)
        cp = np.cos(pitch)
        sp = np.sin(pitch)
        cy = np.cos(yaw)
        sy = np.sin(yaw)
        
        R = np.array([
            [cy*cp, cy*sp*sr - sy*cr, cy*sp*cr + sy*sr],
            [sy*cp, sy*sp*sr + cy*cr, sy*sp*cr - cy*sr],
            [-sp, cp*sr, cp*cr]
        ])
        
        # 4x4齐次变换矩阵
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = [x, y, z]
        
        return T
    
    def camera_info_callback(self, msg: CameraInfo):
        """接收相机内参"""
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.k).reshape(3, 3)
            self.dist_coeffs = np.array(msg.d)
            self.image_size = (msg.width, msg.height)
            self.get_logger().info(f'相机内参已接收: {msg.width}x{msg.height}')
    
    def fusion_callback(self, lidar_msg: DefectArray, vision_msg: DefectArray):
        """时间同步的融合回调"""
        self.get_logger().debug(f'融合: 激光{len(lidar_msg.defects)}个, 视觉{len(vision_msg.defects)}个')
        
        if self.camera_matrix is None:
            self.get_logger().warn('相机内参未接收，跳过融合')
            return
        
        # 执行融合
        fused_defects = self.fuse_defects(lidar_msg.defects, vision_msg.defects)
        
        # 发布融合结果
        fused_msg = DefectArray()
        fused_msg.header = lidar_msg.header
        fused_msg.defects = fused_defects
        
        self.fused_pub.publish(fused_msg)
        self.get_logger().info(f'融合完成: {len(fused_defects)}个最终缺陷')
    
    def fuse_defects(self, lidar_defects, vision_defects):
        """
        核心融合逻辑
        1. 将激光缺陷投影到图像
        2. 与视觉缺陷匹配
        3. 融合置信度与属性
        """
        fused_list = []
        lidar_matched = [False] * len(lidar_defects)
        vision_matched = [False] * len(vision_defects)
        
        # 1. 对每个激光缺陷寻找匹配的视觉缺陷
        for i, lidar_def in enumerate(lidar_defects):
            # 投影激光缺陷到图像
            pixel_coords = self.project_lidar_to_image(lidar_def.position)
            
            if pixel_coords is None:
                # 投影失败或在图像外，仅保留激光检测
                fused_def = self.create_fused_defect(lidar_def, None, 'lidar_only')
                if fused_def.confidence >= self.min_conf:
                    fused_list.append(fused_def)
                continue
            
            # 寻找最近的视觉缺陷
            best_match_idx = None
            min_distance = float('inf')
            
            for j, vision_def in enumerate(vision_defects):
                if vision_matched[j]:
                    continue
                
                # 计算像素距离
                vision_px = (vision_def.position.x, vision_def.position.y)
                distance = np.linalg.norm(np.array(pixel_coords) - np.array(vision_px))
                
                if distance < min_distance:
                    min_distance = distance
                    best_match_idx = j
            
            # 判断是否匹配成功
            if best_match_idx is not None and min_distance < self.image_size[0] * 0.1:  # 10%图像宽度
                # 双重检出，融合
                vision_def = vision_defects[best_match_idx]
                fused_def = self.create_fused_defect(lidar_def, vision_def, 'fusion')
                lidar_matched[i] = True
                vision_matched[best_match_idx] = True
            else:
                # 仅激光检出
                fused_def = self.create_fused_defect(lidar_def, None, 'lidar_only')
            
            if fused_def.confidence >= self.min_conf:
                fused_list.append(fused_def)
        
        # 2. 添加未匹配的视觉缺陷
        for j, vision_def in enumerate(vision_defects):
            if not vision_matched[j]:
                fused_def = self.create_fused_defect(None, vision_def, 'vision_only')
                if fused_def.confidence >= self.min_conf:
                    fused_list.append(fused_def)
        
        return fused_list
    
    def project_lidar_to_image(self, lidar_point):
        """
        将激光坐标系下的3D点投影到图像像素坐标
        返回: (u, v) 或 None
        """
        # 3D点（激光坐标系）
        point_lidar = np.array([lidar_point.x, lidar_point.y, lidar_point.z, 1.0])
        
        # 变换到相机坐标系
        point_camera = self.T_lidar_to_camera @ point_lidar
        
        # 检查深度
        if point_camera[2] <= 0:
            return None
        
        # 投影到归一化平面
        x_norm = point_camera[0] / point_camera[2]
        y_norm = point_camera[1] / point_camera[2]
        
        # 应用相机内参
        u = self.camera_matrix[0, 0] * x_norm + self.camera_matrix[0, 2]
        v = self.camera_matrix[1, 1] * y_norm + self.camera_matrix[1, 2]
        
        # 检查是否在图像范围内
        if 0 <= u < self.image_size[0] and 0 <= v < self.image_size[1]:
            return (u, v)
        else:
            return None
    
    def create_fused_defect(self, lidar_def, vision_def, fusion_type):
        """创建融合后的缺陷信息"""
        self.fusion_counter += 1
        fused = DefectInfo()
        
        if fusion_type == 'fusion':
            # 双重检出，高置信度
            fused.header = lidar_def.header
            fused.defect_id = f'fused_{self.fusion_counter:06d}'
            fused.defect_type = vision_def.defect_type  # 视觉语义更准确
            fused.position = lidar_def.position  # 激光位置更准确
            fused.dimensions = lidar_def.dimensions  # 激光尺寸更准确
            
            # 置信度加权融合并提升
            base_conf = (lidar_def.confidence + vision_def.confidence) / 2.0
            fused.confidence = min(base_conf * self.conf_boost, 1.0)
            
            fused.detection_source = 'fusion'
            fused.severity_level = self.merge_severity(lidar_def.severity_level, vision_def.severity_level)
            
            # 融合属性
            lidar_attr = json.loads(lidar_def.attributes) if lidar_def.attributes else {}
            vision_attr = json.loads(vision_def.attributes) if vision_def.attributes else {}
            fused_attr = {
                'lidar_id': lidar_def.defect_id,
                'vision_id': vision_def.defect_id,
                'fusion_type': 'cross_validated',
                **lidar_attr,
                **vision_attr
            }
            fused.attributes = json.dumps(fused_attr)
            
        elif fusion_type == 'lidar_only':
            # 仅激光检出，惩罚置信度
            fused.header = lidar_def.header
            fused.defect_id = f'fused_{self.fusion_counter:06d}'
            fused.defect_type = lidar_def.defect_type
            fused.position = lidar_def.position
            fused.dimensions = lidar_def.dimensions
            fused.confidence = lidar_def.confidence * self.conf_penalty
            fused.detection_source = 'lidar'
            fused.severity_level = lidar_def.severity_level
            
            attr = json.loads(lidar_def.attributes) if lidar_def.attributes else {}
            attr['fusion_type'] = 'lidar_only'
            fused.attributes = json.dumps(attr)
            
        else:  # vision_only
            # 仅视觉检出，惩罚置信度
            fused.header = vision_def.header
            fused.defect_id = f'fused_{self.fusion_counter:06d}'
            fused.defect_type = vision_def.defect_type
            fused.position = vision_def.position  # 注意：视觉是像素坐标
            fused.dimensions = vision_def.dimensions
            fused.confidence = vision_def.confidence * self.conf_penalty
            fused.detection_source = 'vision'
            fused.severity_level = vision_def.severity_level
            
            attr = json.loads(vision_def.attributes) if vision_def.attributes else {}
            attr['fusion_type'] = 'vision_only'
            fused.attributes = json.dumps(attr)
        
        return fused
    
    def merge_severity(self, sev1, sev2):
        """合并严重程度，取较高者"""
        severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        val1 = severity_order.get(sev1, 1)
        val2 = severity_order.get(sev2, 1)
        max_val = max(val1, val2)
        
        for name, val in severity_order.items():
            if val == max_val:
                return name
        return 'medium'


def main(args=None):
    rclpy.init(args=args)
    node = SensorFusionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
