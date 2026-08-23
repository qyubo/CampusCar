#!/usr/bin/env python3
"""
激光几何缺陷检测节点 - 基于DEM高程差分+欧氏聚类
订阅: /perception/ground_cloud (sensor_msgs/PointCloud2)
发布: /perception/lidar_defects (pavement_interfaces/DefectArray)
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from sensor_msgs.msg import PointCloud2
from pavement_interfaces.msg import DefectArray, DefectInfo
from geometry_msgs.msg import Point, Vector3
import numpy as np
import struct
from collections import defaultdict
import json

# 传感器数据 QoS：BEST_EFFORT，匹配 ground_segmentation 发布端
SENSOR_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=5,
    durability=DurabilityPolicy.VOLATILE,
)


class LidarDefectDetectorNode(Node):
    def __init__(self):
        super().__init__('lidar_defect_detector_node')
        
        # 参数声明
        self.declare_parameter('grid_resolution', 0.05)  # DEM栅格分辨率 5cm
        self.declare_parameter('elevation_threshold_minor', 0.002)  # 2mm异常阈值
        self.declare_parameter('elevation_threshold_major', 0.005)  # 5mm缺陷阈值
        self.declare_parameter('cluster_tolerance', 0.15)  # 聚类距离阈值
        self.declare_parameter('min_cluster_size', 10)
        self.declare_parameter('max_cluster_size', 5000)
        self.declare_parameter('dem_map_path', '')  # 基准DEM地图路径
        self.declare_parameter('defect_id_prefix', 'lidar')
        
        # 获取参数
        self.grid_resolution = self.get_parameter('grid_resolution').value
        self.elev_thresh_minor = self.get_parameter('elevation_threshold_minor').value
        self.elev_thresh_major = self.get_parameter('elevation_threshold_major').value
        self.cluster_tol = self.get_parameter('cluster_tolerance').value
        self.min_cluster = self.get_parameter('min_cluster_size').value
        self.max_cluster = self.get_parameter('max_cluster_size').value
        self.dem_map_path = self.get_parameter('dem_map_path').value
        self.defect_id_prefix = self.get_parameter('defect_id_prefix').value
        
        # 初始化基准DEM地图
        self.baseline_dem = {}  # {(grid_x, grid_y): baseline_elevation}
        self.dem_initialized = False
        self.initialization_frames = 0
        self.max_init_frames = 20  # 用前20帧初始化DEM
        
        if self.dem_map_path:
            self.load_dem_map(self.dem_map_path)
        
        # 订阅与发布（订阅用 SENSOR_QOS 匹配 ground_segmentation 发布端）
        self.ground_sub = self.create_subscription(
            PointCloud2, '/perception/ground_cloud', self.ground_callback, SENSOR_QOS)
        self.defect_pub = self.create_publisher(DefectArray, '/perception/lidar_defects', 10)
        
        self.defect_counter = 0
        
        self.get_logger().info('激光缺陷检测节点已启动')
        self.get_logger().info(f'DEM分辨率: {self.grid_resolution}m, 阈值: {self.elev_thresh_major*1000}mm')
    
    def load_dem_map(self, path):
        """加载预先构建的DEM基准地图"""
        try:
            import pickle
            with open(path, 'rb') as f:
                self.baseline_dem = pickle.load(f)
            self.dem_initialized = True
            self.get_logger().info(f'已加载DEM地图: {len(self.baseline_dem)}个栅格')
        except Exception as e:
            self.get_logger().warn(f'加载DEM失败: {e}，将在线初始化')
    
    def ground_callback(self, msg: PointCloud2):
        """地面点云回调"""
        try:
            points = self.parse_pointcloud(msg)
            if points is None or len(points) < 10:
                return

            # 如果DEM未初始化，先累积数据初始化
            if not self.dem_initialized:
                self.initialize_dem(points)
                if self.initialization_frames < self.max_init_frames:
                    return

            # 执行缺陷检测
            defect_array = self.detect_defects(points, msg.header)
            if len(defect_array.defects) > 0:
                self.defect_pub.publish(defect_array)
                self.get_logger().info(f'检测到 {len(defect_array.defects)} 个激光缺陷')
        except Exception as e:
            self.get_logger().error(f'缺陷检测回调异常: {e}', throttle_duration_sec=5.0)

    def parse_pointcloud(self, msg: PointCloud2):
        """解析PointCloud2消息（numpy向量化，兼容任意 point_step）"""
        try:
            field_map = {f.name: f for f in msg.fields}
            if not all(n in field_map for n in ('x', 'y', 'z')):
                return None

            point_step = msg.point_step
            num_points = msg.width * msg.height
            if num_points == 0 or point_step == 0:
                return None

            raw = np.frombuffer(bytes(msg.data), dtype=np.uint8).reshape(-1, point_step)
            x = np.frombuffer(raw[:, field_map['x'].offset:field_map['x'].offset+4].tobytes(), dtype=np.float32)
            y = np.frombuffer(raw[:, field_map['y'].offset:field_map['y'].offset+4].tobytes(), dtype=np.float32)
            z = np.frombuffer(raw[:, field_map['z'].offset:field_map['z'].offset+4].tobytes(), dtype=np.float32)
            if 'intensity' in field_map:
                i_off = field_map['intensity'].offset
                intensity = np.frombuffer(raw[:, i_off:i_off+4].tobytes(), dtype=np.float32)
            else:
                intensity = np.zeros(num_points, dtype=np.float32)

            return np.column_stack((x, y, z, intensity))
        except Exception as e:
            self.get_logger().error(f'解析点云失败: {e}', throttle_duration_sec=5.0)
            return None
    
    def initialize_dem(self, points):
        """在线初始化基准DEM"""
        self.initialization_frames += 1
        
        for point in points:
            grid_key = self.world_to_grid(point[0], point[1])
            
            if grid_key not in self.baseline_dem:
                self.baseline_dem[grid_key] = []
            
            self.baseline_dem[grid_key].append(point[2])
        
        # 达到初始化帧数后，对每个栅格取中位数作为基准高程
        if self.initialization_frames >= self.max_init_frames:
            for grid_key in self.baseline_dem:
                heights = self.baseline_dem[grid_key]
                self.baseline_dem[grid_key] = np.median(heights)
            
            self.dem_initialized = True
            self.get_logger().info(f'DEM初始化完成: {len(self.baseline_dem)}个栅格')
    
    def world_to_grid(self, x, y):
        """世界坐标转换为栅格坐标"""
        grid_x = int(np.floor(x / self.grid_resolution))
        grid_y = int(np.floor(y / self.grid_resolution))
        return (grid_x, grid_y)
    
    def grid_to_world(self, grid_x, grid_y):
        """栅格坐标转换为世界坐标（中心点）"""
        x = (grid_x + 0.5) * self.grid_resolution
        y = (grid_y + 0.5) * self.grid_resolution
        return x, y
    
    def detect_defects(self, points, header):
        """
        缺陷检测：DEM高程差分 + 局部中位数高程检测
        1. DEM偏差：检测相对基准DEM的高程变化（新出现的异常）
        2. 局部中位数：检测相对当前帧地面中位数的高程偏离（持久性缺陷，如DEM初始化时已包含的坑槽）
        3. 欧氏距离聚类
        4. 提取缺陷特征
        """
        defect_array = DefectArray()
        defect_array.header = header

        # 计算当前帧地面高程中位数（鲁棒的局部地面基准）
        local_ground_z = float(np.median(points[:, 2]))

        # 1. 高程差分（DEM偏差 + 局部中位数偏差）
        anomaly_points = []
        anomaly_deviations = []

        for point in points:
            grid_key = self.world_to_grid(point[0], point[1])
            deviation = 0.0
            is_anomaly = False

            # DEM偏差检测（仅对基准DEM中已存在的栅格）
            if grid_key in self.baseline_dem:
                baseline_elev = self.baseline_dem[grid_key]
                dem_dev = abs(point[2] - baseline_elev)
                if dem_dev > self.elev_thresh_major:
                    is_anomaly = True
                    deviation = max(deviation, dem_dev)

            # 局部中位数偏差检测（捕获DEM初始化时已包含的缺陷）
            local_dev = abs(point[2] - local_ground_z)
            if local_dev > self.elev_thresh_major:
                is_anomaly = True
                deviation = max(deviation, local_dev)

            if is_anomaly:
                anomaly_points.append(point[:3])
                anomaly_deviations.append(deviation)

        if len(anomaly_points) < self.min_cluster:
            self.get_logger().info(
                f'地面中位数z={local_ground_z:.4f}, 异常点={len(anomaly_points)} (<{self.min_cluster}), '
                f'z范围=[{points[:,2].min():.4f}, {points[:,2].max():.4f}]',
                throttle_duration_sec=10.0)
            return defect_array

        # 限制聚类点数上限，防止 O(n²) 挂死
        MAX_CLUSTER_INPUT = 500
        if len(anomaly_points) > MAX_CLUSTER_INPUT:
            # 按偏差大小排序，只取最显著的 MAX_CLUSTER_INPUT 个点
            sorted_idx = np.argsort(anomaly_deviations)[::-1][:MAX_CLUSTER_INPUT]
            anomaly_points = [anomaly_points[i] for i in sorted_idx]
            anomaly_deviations = [anomaly_deviations[i] for i in sorted_idx]
            self.get_logger().warn(f'异常点过多({len(anomaly_points)})，截取前{MAX_CLUSTER_INPUT}个聚类')

        anomaly_points = np.array(anomaly_points)
        anomaly_deviations = np.array(anomaly_deviations)
        
        # 2. 欧氏距离聚类
        clusters = self.euclidean_clustering(anomaly_points)
        
        # 3. 提取每个簇的缺陷特征
        for cluster_indices in clusters:
            if len(cluster_indices) < self.min_cluster or len(cluster_indices) > self.max_cluster:
                continue
            
            cluster_points = anomaly_points[cluster_indices]
            cluster_deviations = anomaly_deviations[cluster_indices]
            
            defect = self.extract_defect_features(cluster_points, cluster_deviations, header)
            defect_array.defects.append(defect)
        
        return defect_array
    
    def euclidean_clustering(self, points):
        """
        简化的欧氏距离聚类算法
        返回: list of list，每个子列表包含属于同一簇的点索引
        """
        n_points = len(points)
        visited = np.zeros(n_points, dtype=bool)
        clusters = []
        
        for i in range(n_points):
            if visited[i]:
                continue
            
            # 开始新簇
            cluster = [i]
            visited[i] = True
            queue = [i]
            
            while queue:
                current_idx = queue.pop(0)
                current_point = points[current_idx]
                
                # 查找未访问的邻居
                for j in range(n_points):
                    if visited[j]:
                        continue
                    
                    distance = np.linalg.norm(points[j] - current_point)
                    if distance < self.cluster_tol:
                        cluster.append(j)
                        visited[j] = True
                        queue.append(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def extract_defect_features(self, cluster_points, cluster_deviations, header):
        """提取缺陷特征"""
        defect = DefectInfo()
        defect.header = header
        
        # 生成唯一ID
        self.defect_counter += 1
        defect.defect_id = f'{self.defect_id_prefix}_{self.defect_counter:06d}'
        
        # 计算中心位置
        centroid = np.mean(cluster_points, axis=0)
        defect.position = Point(x=float(centroid[0]), y=float(centroid[1]), z=float(centroid[2]))
        
        # 计算三维尺寸（包围盒）
        min_bounds = np.min(cluster_points, axis=0)
        max_bounds = np.max(cluster_points, axis=0)
        dimensions = max_bounds - min_bounds
        defect.dimensions = Vector3(
            x=float(dimensions[0]),
            y=float(dimensions[1]),
            z=float(np.max(cluster_deviations))  # 深度用最大高程偏差
        )
        
        # 置信度：基于聚类点数和平均高程偏差
        point_confidence = min(len(cluster_points) / 100.0, 1.0)
        deviation_confidence = min(np.mean(cluster_deviations) / 0.02, 1.0)
        defect.confidence = float((point_confidence + deviation_confidence) / 2.0)
        
        # 检测来源
        defect.detection_source = 'lidar'
        
        # 根据尺寸和深度判断缺陷类型
        area = dimensions[0] * dimensions[1]
        depth = dimensions[2]
        
        if depth > 0.03 and area > 0.01:
            defect.defect_type = 'pothole'  # 坑槽
            defect.severity_level = 'high'
        elif depth > 0.01:
            defect.defect_type = 'depression'  # 沉降
            defect.severity_level = 'medium'
        else:
            defect.defect_type = 'crack'  # 裂缝
            defect.severity_level = 'low'
        
        # 附加属性
        attributes = {
            'cluster_size': len(cluster_points),
            'mean_deviation': float(np.mean(cluster_deviations)),
            'max_deviation': float(np.max(cluster_deviations)),
            'volume': float(area * depth)
        }
        defect.attributes = json.dumps(attributes)
        
        return defect


def main(args=None):
    rclpy.init(args=args)
    node = LidarDefectDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
