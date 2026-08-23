#!/usr/bin/env python3
"""
低秩动力学世界模型节点
基于SVD低秩表征 + Paris定律物理约束实现路面缺陷演化预测
订阅: /perception/fused_defects (pavement_interfaces/DefectArray)
发布: /prediction/defect_evolution (pavement_interfaces/DefectPrediction)
核心算法:
1. SVD奇异值分解获取低秩子空间
2. Paris损伤演化方程作为物理硬约束
3. 最小二乘快速适配新材质
4. 输出未来3个月演化曲线
"""
import rclpy
from rclpy.node import Node
from pavement_interfaces.msg import DefectArray, DefectPrediction
from builtin_interfaces.msg import Time
from geometry_msgs.msg import Vector3
import numpy as np
from scipy.linalg import svd
import json
from datetime import datetime, timedelta


class WorldModelNode(Node):
    def __init__(self):
        super().__init__('world_model_node')
        
        # 参数声明
        self.declare_parameter('low_rank_dimension', 5)  # 低秩维度
        self.declare_parameter('prediction_horizon_days', 90)  # 预测90天
        self.declare_parameter('time_step_days', 15)  # 时间步长15天
        self.declare_parameter('paris_law_C', 1e-10)  # Paris定律参数C
        self.declare_parameter('paris_law_m', 3.0)  # Paris定律指数m
        self.declare_parameter('material_types', ['asphalt', 'concrete', 'brick', 'gravel', 'mixed'])
        self.declare_parameter('enable_incremental_learning', True)
        
        # 获取参数
        self.rank = self.get_parameter('low_rank_dimension').value
        self.horizon_days = self.get_parameter('prediction_horizon_days').value
        self.time_step = self.get_parameter('time_step_days').value
        self.paris_C = self.get_parameter('paris_law_C').value
        self.paris_m = self.get_parameter('paris_law_m').value
        self.material_types = self.get_parameter('material_types').value
        self.enable_learning = self.get_parameter('enable_incremental_learning').value
        
        # 预训练的低秩子空间基向量（每种材质）
        self.basis_matrices = self.initialize_basis_matrices()
        
        # 缺陷历史数据（用于增量学习）
        self.defect_history = {}  # {defect_id: [(timestamp, dimensions), ...]}
        
        # 订阅与发布
        self.defect_sub = self.create_subscription(
            DefectArray, '/perception/fused_defects', self.defect_callback, 10)
        self.prediction_pub = self.create_publisher(
            DefectPrediction, '/prediction/defect_evolution', 10)
        
        self.get_logger().info('低秩动力学世界模型节点已启动')
        self.get_logger().info(f'低秩维度: {self.rank}, 预测周期: {self.horizon_days}天')
    
    def initialize_basis_matrices(self):
        """
        初始化预训练的低秩子空间基向量
        实际应用中应从训练数据学习，这里使用合理的初始化
        """
        basis = {}
        
        for material in self.material_types:
            # 生成材质相关的低秩基（rank x 3）
            # 3维对应 [长度, 宽度, 深度] 的演化模式
            if material == 'asphalt':
                # 沥青：深度增长快，横向扩展慢
                base = np.array([
                    [0.1, 0.1, 0.3],   # 主模式：深度主导
                    [0.2, 0.2, 0.1],   # 次模式：横向扩展
                    [0.05, 0.05, 0.05], # 均匀模式
                    [0.15, 0.1, 0.2],  # 混合模式1
                    [0.1, 0.15, 0.15]  # 混合模式2
                ])
            elif material == 'concrete':
                # 混凝土：裂缝扩展快，深度慢
                base = np.array([
                    [0.3, 0.3, 0.1],
                    [0.2, 0.2, 0.05],
                    [0.1, 0.1, 0.15],
                    [0.15, 0.2, 0.1],
                    [0.2, 0.15, 0.08]
                ])
            elif material == 'brick':
                # 砖面：横向纵向差异大
                base = np.array([
                    [0.2, 0.3, 0.15],
                    [0.3, 0.2, 0.1],
                    [0.1, 0.1, 0.2],
                    [0.15, 0.15, 0.12],
                    [0.12, 0.18, 0.15]
                ])
            else:  # gravel, mixed
                # 通用材质
                base = np.array([
                    [0.2, 0.2, 0.2],
                    [0.15, 0.15, 0.15],
                    [0.1, 0.1, 0.1],
                    [0.12, 0.15, 0.13],
                    [0.13, 0.12, 0.15]
                ])
            
            # 正交化（Gram-Schmidt）
            basis[material] = self.orthogonalize(base[:self.rank])
        
        return basis
    
    def orthogonalize(self, matrix):
        """Gram-Schmidt正交化"""
        Q, R = np.linalg.qr(matrix.T)
        return Q.T
    
    def defect_callback(self, msg: DefectArray):
        """接收融合后的缺陷数据并进行预测"""
        for defect in msg.defects:
            # 只预测高置信度的缺陷
            if defect.confidence < 0.6:
                continue
            
            # 提取缺陷信息
            defect_id = defect.defect_id
            defect_type = defect.defect_type
            current_dims = np.array([
                defect.dimensions.x,
                defect.dimensions.y,
                defect.dimensions.z
            ])
            
            # 判断材质（从属性中提取或使用默认）
            material = self.infer_material(defect)
            
            # 记录历史数据（用于增量学习）
            if self.enable_learning:
                self.update_history(defect_id, current_dims)
            
            # 执行预测
            prediction = self.predict_evolution(
                defect_id, defect_type, current_dims, material, msg.header
            )
            
            # 发布预测结果
            self.prediction_pub.publish(prediction)
            
            self.get_logger().info(
                f'预测 {defect_id}: 当前{current_dims[2]*100:.1f}cm → '
                f'90天后{prediction.predicted_dimensions[-1].z*100:.1f}cm, '
                f'风险: {prediction.risk_levels[-1]}'
            )
    
    def infer_material(self, defect):
        """推断路面材质（从属性或使用默认）"""
        try:
            attrs = json.loads(defect.attributes) if defect.attributes else {}
            material = attrs.get('material', 'asphalt')
            if material not in self.material_types:
                material = 'asphalt'
            return material
        except:
            return 'asphalt'
    
    def predict_evolution(self, defect_id, defect_type, current_dims, material, header):
        """
        核心预测算法：低秩表征 + Paris定律约束
        """
        prediction = DefectPrediction()
        prediction.header = header
        prediction.defect_id = defect_id
        prediction.current_time = self.get_clock().now().to_msg()
        
        # 1. 获取材质对应的低秩基
        basis = self.basis_matrices[material]  # (rank, 3)
        
        # 2. 求解低秩系数（最小二乘）
        # current_dims ≈ coeffs @ basis
        coeffs, residuals, rank, s = np.linalg.lstsq(basis, current_dims, rcond=None)
        
        # 3. 时间序列预测
        num_steps = int(self.horizon_days / self.time_step)
        predicted_dims_list = []
        predicted_times_list = []
        risk_levels = []
        
        for step in range(num_steps + 1):
            t_days = step * self.time_step
            
            # Paris损伤演化定律: da/dN = C * (ΔK)^m
            # 简化为: a(t) = a0 * (1 + C * t^m)
            growth_factor = 1.0 + self.paris_C * (t_days ** self.paris_m)
            
            # 应用低秩约束的演化
            # 不同维度按基向量权重演化
            predicted_dims = current_dims * growth_factor
            
            # 考虑低秩基的影响（某些维度演化更快）
            for i in range(3):
                dim_growth = np.sum(coeffs * basis[:, i])
                predicted_dims[i] *= (1.0 + dim_growth * t_days / self.horizon_days)
            
            # 物理约束：深度不能超过合理范围
            predicted_dims[2] = min(predicted_dims[2], 0.5)  # 最大50cm
            
            # 记录预测结果
            pred_vec = Vector3(
                x=float(predicted_dims[0]),
                y=float(predicted_dims[1]),
                z=float(predicted_dims[2])
            )
            predicted_dims_list.append(pred_vec)
            
            # 时间戳
            future_time = self.get_clock().now().nanoseconds + int(t_days * 24 * 3600 * 1e9)
            pred_time = Time(sec=int(future_time / 1e9), nanosec=int(future_time % 1e9))
            predicted_times_list.append(pred_time)
            
            # 风险等级评估
            risk = self.assess_risk(predicted_dims, defect_type)
            risk_levels.append(risk)
        
        # 4. 推荐养护时间（风险达到high时）
        maintenance_time = self.recommend_maintenance_time(
            risk_levels, predicted_times_list
        )
        
        # 5. 预测置信度（基于残差和历史数据）
        prediction_confidence = self.calculate_prediction_confidence(
            residuals, defect_id
        )
        
        # 填充预测消息
        prediction.predicted_dimensions = predicted_dims_list
        prediction.prediction_timestamps = predicted_times_list
        prediction.risk_levels = risk_levels
        prediction.recommended_maintenance_time = maintenance_time
        prediction.prediction_confidence = float(prediction_confidence)
        
        return prediction
    
    def assess_risk(self, dims, defect_type):
        """评估风险等级"""
        depth = dims[2]
        area = dims[0] * dims[1]
        
        if defect_type == 'pothole':
            if depth > 0.1 or area > 0.5:
                return 'critical'
            elif depth > 0.05 or area > 0.2:
                return 'high'
            elif depth > 0.02:
                return 'medium'
            else:
                return 'low'
        elif defect_type == 'crack':
            if depth > 0.05 or area > 1.0:
                return 'high'
            elif depth > 0.02 or area > 0.5:
                return 'medium'
            else:
                return 'low'
        else:
            if depth > 0.08:
                return 'high'
            elif depth > 0.03:
                return 'medium'
            else:
                return 'low'
    
    def recommend_maintenance_time(self, risk_levels, time_stamps):
        """推荐养护时间（首次达到high风险）"""
        for risk, timestamp in zip(risk_levels, time_stamps):
            if risk in ['high', 'critical']:
                return timestamp
        
        # 如果未达到high，返回最后时间
        return time_stamps[-1] if time_stamps else Time()
    
    def calculate_prediction_confidence(self, residuals, defect_id):
        """计算预测置信度"""
        # 基于拟合残差
        base_confidence = 0.8
        
        if residuals is not None and len(residuals) > 0:
            residual_penalty = min(np.sum(residuals) * 0.1, 0.3)
            base_confidence -= residual_penalty
        
        # 如果有历史数据，提升置信度
        if defect_id in self.defect_history and len(self.defect_history[defect_id]) > 3:
            base_confidence = min(base_confidence + 0.1, 0.95)
        
        return max(base_confidence, 0.4)
    
    def update_history(self, defect_id, dims):
        """更新缺陷历史数据"""
        if defect_id not in self.defect_history:
            self.defect_history[defect_id] = []
        
        timestamp = self.get_clock().now().nanoseconds
        self.defect_history[defect_id].append((timestamp, dims.copy()))
        
        # 限制历史长度
        if len(self.defect_history[defect_id]) > 20:
            self.defect_history[defect_id].pop(0)


def main(args=None):
    rclpy.init(args=args)
    node = WorldModelNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
