#!/usr/bin/env python3
"""
动态数字路面地图节点
维护四维路面地图（几何+语义+预测+时间），支持增量更新和服务查询

订阅: /perception/fused_defects (pavement_interfaces/DefectArray)
订阅: /prediction/defect_evolution (pavement_interfaces/DefectPrediction)
发布: /roadmap/map_update (std_msgs/String) - 增量更新通知
提供服务: /roadmap/query_condition (pavement_interfaces/srv/QueryRoadCondition)
提供服务: /roadmap/request_detour (pavement_interfaces/srv/RequestDetourPath)

核心数据结构:
- 多层栅格地图（基础高程、材质语义、缺陷标记、预测风险）
- 增量式更新（仅更新变化区域）
- 空间索引（快速查询）
"""
import rclpy
from rclpy.node import Node
from pavement_interfaces.msg import DefectArray, DefectInfo, DefectPrediction, RoadCondition
from pavement_interfaces.srv import QueryRoadCondition, RequestDetourPath
from std_msgs.msg import String
from geometry_msgs.msg import Point, PoseStamped
import numpy as np
from collections import defaultdict
import json
import pickle
import os


class DynamicRoadmapNode(Node):
    def __init__(self):
        super().__init__('dynamic_roadmap_node')
        
        # 参数声明
        self.declare_parameter('grid_resolution', 0.5)  # 栅格分辨率50cm
        self.declare_parameter('map_size_x', 200.0)  # 地图尺寸200m x 200m
        self.declare_parameter('map_size_y', 200.0)
        self.declare_parameter('map_origin_x', -100.0)
        self.declare_parameter('map_origin_y', -100.0)
        self.declare_parameter('enable_persistence', True)
        self.declare_parameter('map_save_path', '~/roadmap_data.pkl')
        self.declare_parameter('quality_score_weight_density', 0.4)
        self.declare_parameter('quality_score_weight_severity', 0.6)
        
        # 获取参数
        self.resolution = self.get_parameter('grid_resolution').value
        self.size_x = self.get_parameter('map_size_x').value
        self.size_y = self.get_parameter('map_size_y').value
        self.origin_x = self.get_parameter('map_origin_x').value
        self.origin_y = self.get_parameter('map_origin_y').value
        self.enable_save = self.get_parameter('enable_persistence').value
        self.save_path = os.path.expanduser(self.get_parameter('map_save_path').value)
        self.w_density = self.get_parameter('quality_score_weight_density').value
        self.w_severity = self.get_parameter('quality_score_weight_severity').value
        
        # 计算栅格数量
        self.grid_nx = int(self.size_x / self.resolution)
        self.grid_ny = int(self.size_y / self.resolution)
        
        # 初始化多层地图
        self.elevation_map = np.zeros((self.grid_nx, self.grid_ny), dtype=np.float32)
        self.material_map = np.zeros((self.grid_nx, self.grid_ny), dtype=np.uint8)  # 材质ID
        self.defect_map = {}  # {(gx, gy): [DefectInfo, ...]}
        self.risk_map = np.zeros((self.grid_nx, self.grid_ny), dtype=np.uint8)  # 0-4对应low/medium/high/critical
        self.prediction_map = {}  # {defect_id: DefectPrediction}
        
        # 材质映射
        self.material_names = ['unknown', 'asphalt', 'concrete', 'brick', 'gravel', 'mixed']
        self.risk_mapping = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        
        # 加载持久化地图
        if self.enable_save:
            self.load_map()
        
        # 订阅
        self.defect_sub = self.create_subscription(
            DefectArray, '/perception/fused_defects', self.defect_callback, 10)
        self.prediction_sub = self.create_subscription(
            DefectPrediction, '/prediction/defect_evolution', self.prediction_callback, 10)
        
        # 发布
        self.update_pub = self.create_publisher(String, '/roadmap/map_update', 10)
        
        # 服务
        self.query_srv = self.create_service(
            QueryRoadCondition, '/roadmap/query_condition', self.query_callback)
        self.detour_srv = self.create_service(
            RequestDetourPath, '/roadmap/request_detour', self.detour_callback)
        
        # 定时保存
        if self.enable_save:
            self.save_timer = self.create_timer(300.0, self.save_map)  # 5分钟保存一次
        
        self.get_logger().info('动态数字路面地图节点已启动')
        self.get_logger().info(f'地图尺寸: {self.grid_nx}x{self.grid_ny}, 分辨率: {self.resolution}m')
    
    def world_to_grid(self, x, y):
        """世界坐标转栅格坐标"""
        gx = int((x - self.origin_x) / self.resolution)
        gy = int((y - self.origin_y) / self.resolution)
        return gx, gy
    
    def grid_to_world(self, gx, gy):
        """栅格坐标转世界坐标（中心）"""
        x = self.origin_x + (gx + 0.5) * self.resolution
        y = self.origin_y + (gy + 0.5) * self.resolution
        return x, y
    
    def is_valid_grid(self, gx, gy):
        """检查栅格坐标是否有效"""
        return 0 <= gx < self.grid_nx and 0 <= gy < self.grid_ny
    
    def defect_callback(self, msg: DefectArray):
        """接收缺陷数据，增量更新地图"""
        updated_grids = set()
        
        for defect in msg.defects:
            # 转换到栅格坐标
            gx, gy = self.world_to_grid(defect.position.x, defect.position.y)
            
            if not self.is_valid_grid(gx, gy):
                continue
            
            # 更新缺陷层
            grid_key = (gx, gy)
            if grid_key not in self.defect_map:
                self.defect_map[grid_key] = []
            
            # 检查是否已存在（按ID去重）
            existing_ids = [d.defect_id for d in self.defect_map[grid_key]]
            if defect.defect_id not in existing_ids:
                self.defect_map[grid_key].append(defect)
            else:
                # 更新现有缺陷
                for i, d in enumerate(self.defect_map[grid_key]):
                    if d.defect_id == defect.defect_id:
                        self.defect_map[grid_key][i] = defect
                        break
            
            # 更新风险层
            risk_level = defect.severity_level
            risk_value = self.risk_mapping.get(risk_level, 1)
            self.risk_map[gx, gy] = max(self.risk_map[gx, gy], risk_value)
            
            # 更新材质层（从属性推断）
            material = self.infer_material(defect)
            material_id = self.material_names.index(material) if material in self.material_names else 0
            if self.material_map[gx, gy] == 0:
                self.material_map[gx, gy] = material_id
            
            updated_grids.add(grid_key)
        
        # 发布更新通知
        if updated_grids:
            update_msg = String()
            update_msg.data = json.dumps({
                'updated_grids': list(updated_grids),
                'num_defects': len(msg.defects)
            })
            self.update_pub.publish(update_msg)
            
            self.get_logger().info(f'地图更新: {len(updated_grids)}个栅格, {len(msg.defects)}个缺陷')
    
    def prediction_callback(self, msg: DefectPrediction):
        """接收预测数据，更新预测层"""
        self.prediction_map[msg.defect_id] = msg
        self.get_logger().debug(f'更新预测: {msg.defect_id}')
    
    def infer_material(self, defect):
        """从缺陷属性推断材质"""
        try:
            attrs = json.loads(defect.attributes) if defect.attributes else {}
            return attrs.get('material', 'asphalt')
        except:
            return 'asphalt'
    
    def query_callback(self, request, response):
        """
        路况查询服务
        输入: 中心点+半径
        输出: 该区域的路况综合信息
        """
        # 转换查询区域到栅格
        center_x = request.query_center.x
        center_y = request.query_center.y
        radius = request.query_radius
        
        gx_center, gy_center = self.world_to_grid(center_x, center_y)
        grid_radius = int(radius / self.resolution) + 1
        
        # 收集区域内的缺陷
        defects_in_region = []
        risk_values = []
        
        for gx in range(max(0, gx_center - grid_radius), 
                       min(self.grid_nx, gx_center + grid_radius + 1)):
            for gy in range(max(0, gy_center - grid_radius),
                           min(self.grid_ny, gy_center + grid_radius + 1)):
                # 检查是否在圆形区域内
                wx, wy = self.grid_to_world(gx, gy)
                dist = np.sqrt((wx - center_x)**2 + (wy - center_y)**2)
                
                if dist <= radius:
                    grid_key = (gx, gy)
                    if grid_key in self.defect_map:
                        defects_in_region.extend(self.defect_map[grid_key])
                    
                    risk_values.append(self.risk_map[gx, gy])
        
        # 计算路况评分（0-10分）
        quality_score = self.calculate_quality_score(
            defects_in_region, risk_values, radius
        )
        
        # 给出通行建议
        traffic_advice = self.generate_traffic_advice(quality_score, risk_values)
        
        # 构造响应
        road_condition = RoadCondition()
        road_condition.header.stamp = self.get_clock().now().to_msg()
        road_condition.header.frame_id = 'map'
        road_condition.center = request.query_center
        road_condition.radius = radius
        road_condition.defects = defects_in_region
        road_condition.road_quality_score = quality_score
        road_condition.traffic_advice = traffic_advice
        
        response.road_condition = road_condition
        response.success = True
        response.message = f'查询成功: 区域内{len(defects_in_region)}个缺陷, 评分{quality_score:.1f}'
        
        self.get_logger().info(response.message)
        return response
    
    def calculate_quality_score(self, defects, risk_values, radius):
        """
        计算路况质量评分（0-10）
        考虑缺陷密度和严重程度
        """
        # 基础分10分
        base_score = 10.0
        
        # 密度惩罚
        area = np.pi * radius ** 2
        defect_density = len(defects) / area if area > 0 else 0
        density_penalty = min(defect_density * 2.0, 5.0)  # 最多扣5分
        
        # 严重程度惩罚
        avg_risk = np.mean(risk_values) if len(risk_values) > 0 else 0
        severity_penalty = avg_risk * 1.5  # 最多扣6分（critical=4, 4*1.5=6）
        
        # 加权计算
        total_penalty = (self.w_density * density_penalty + 
                        self.w_severity * severity_penalty)
        
        final_score = max(base_score - total_penalty, 0.0)
        return float(final_score)
    
    def generate_traffic_advice(self, quality_score, risk_values):
        """生成通行建议"""
        max_risk = np.max(risk_values) if len(risk_values) > 0 else 0
        
        if max_risk >= 4 or quality_score < 3.0:
            return 'avoid'  # 避免通行
        elif max_risk >= 3 or quality_score < 6.0:
            return 'caution'  # 谨慎通行
        else:
            return 'safe'  # 安全通行
    
    def detour_callback(self, request, response):
        """
        绕行路径规划服务
        简化实现：基于A*算法，避开高风险区域
        """
        start_x = request.start_position.x
        start_y = request.start_position.y
        goal_x = request.goal_position.x
        goal_y = request.goal_position.y
        
        # 转换到栅格
        start_gx, start_gy = self.world_to_grid(start_x, start_y)
        goal_gx, goal_gy = self.world_to_grid(goal_x, goal_y)
        
        # 简化实现：直线路径，避开高风险点
        path = self.plan_simple_detour(
            (start_gx, start_gy), (goal_gx, goal_gy), 
            request.avoid_defect_ids
        )
        
        # 转换回世界坐标
        path_poses = []
        for gx, gy in path:
            wx, wy = self.grid_to_world(gx, gy)
            pose = PoseStamped()
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.header.frame_id = 'map'
            pose.pose.position.x = wx
            pose.pose.position.y = wy
            pose.pose.position.z = 0.0
            path_poses.append(pose)
        
        # 计算距离和时间（假设速度0.5m/s）
        distance = len(path) * self.resolution
        duration = distance / 0.5
        
        response.detour_path = path_poses
        response.estimated_distance = float(distance)
        response.estimated_duration = float(duration)
        response.success = len(path) > 0
        response.message = f'规划成功: {len(path)}个航点, 距离{distance:.1f}m'
        
        self.get_logger().info(response.message)
        return response
    
    def plan_simple_detour(self, start, goal, avoid_ids):
        """
        简化的绕行规划：直线插值+避障
        """
        path = []
        gx0, gy0 = start
        gx1, gy1 = goal
        
        # Bresenham直线插值
        dx = abs(gx1 - gx0)
        dy = abs(gy1 - gy0)
        sx = 1 if gx0 < gx1 else -1
        sy = 1 if gy0 < gy1 else -1
        err = dx - dy
        
        gx, gy = gx0, gy0
        
        while True:
            # 检查当前点是否安全
            if self.is_valid_grid(gx, gy):
                # 如果是高风险区，尝试绕行
                if self.risk_map[gx, gy] >= 3:
                    # 简单策略：向垂直方向偏移
                    offset_dir = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    for dx_off, dy_off in offset_dir:
                        gx_new = gx + dx_off
                        gy_new = gy + dy_off
                        if self.is_valid_grid(gx_new, gy_new) and self.risk_map[gx_new, gy_new] < 3:
                            path.append((gx_new, gy_new))
                            break
                    else:
                        path.append((gx, gy))  # 无法绕行，保留原路径
                else:
                    path.append((gx, gy))
            
            if gx == gx1 and gy == gy1:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                gx += sx
            if e2 < dx:
                err += dx
                gy += sy
        
        return path
    
    def save_map(self):
        """保存地图到文件"""
        try:
            map_data = {
                'elevation_map': self.elevation_map,
                'material_map': self.material_map,
                'defect_map': self.defect_map,
                'risk_map': self.risk_map,
                'prediction_map': self.prediction_map,
                'metadata': {
                    'resolution': self.resolution,
                    'size': (self.grid_nx, self.grid_ny),
                    'origin': (self.origin_x, self.origin_y)
                }
            }
            
            with open(self.save_path, 'wb') as f:
                pickle.dump(map_data, f)
            
            self.get_logger().info(f'地图已保存: {self.save_path}')
        except Exception as e:
            self.get_logger().error(f'地图保存失败: {e}')
    
    def load_map(self):
        """从文件加载地图"""
        if not os.path.exists(self.save_path):
            self.get_logger().info('未找到已保存的地图，使用新地图')
            return
        
        try:
            with open(self.save_path, 'rb') as f:
                map_data = pickle.load(f)
            
            self.elevation_map = map_data['elevation_map']
            self.material_map = map_data['material_map']
            self.defect_map = map_data['defect_map']
            self.risk_map = map_data['risk_map']
            self.prediction_map = map_data['prediction_map']
            
            self.get_logger().info(f'地图已加载: {self.save_path}')
            self.get_logger().info(f'包含 {len(self.defect_map)} 个栅格的缺陷数据')
        except Exception as e:
            self.get_logger().error(f'地图加载失败: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = DynamicRoadmapNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # 退出时保存地图
        if node.enable_save:
            node.save_map()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
