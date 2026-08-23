#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
世界模型演化预测 - 可视化Demo
展示低秩动力学模型 + Paris定律的缺陷演化预测
"""
import sys
import io
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非GUI后端
from pathlib import Path
from datetime import datetime, timedelta

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

print("="*70)
print("世界模型演化预测 - Demo")
print("低秩动力学 + Paris定律")
print("="*70)
print()

# 模拟缺陷数据
class DefectEvolutionSimulator:
    def __init__(self):
        # Paris定律参数
        self.paris_C = 1e-10
        self.paris_m = 3.0
        
        # 低秩基向量（5种材质）
        self.materials = {
            'asphalt': np.array([
                [0.1, 0.1, 0.3],   # 深度主导
                [0.2, 0.2, 0.1],
                [0.05, 0.05, 0.05],
                [0.15, 0.1, 0.2],
                [0.1, 0.15, 0.15]
            ]),
            'concrete': np.array([
                [0.3, 0.3, 0.1],   # 横向主导
                [0.2, 0.2, 0.05],
                [0.1, 0.1, 0.15],
                [0.15, 0.2, 0.1],
                [0.2, 0.15, 0.08]
            ])
        }
    
    def predict_evolution(self, initial_dims, material='asphalt', days=90):
        """
        预测缺陷演化
        initial_dims: [长度, 宽度, 深度] 单位米
        """
        basis = self.materials[material][:3]  # 使用前3个基向量
        
        # 低秩系数求解
        coeffs, _, _, _ = np.linalg.lstsq(basis, initial_dims, rcond=None)
        
        # 时间序列
        time_points = np.linspace(0, days, 7)  # 0, 15, 30, ..., 90天
        predictions = []
        
        for t_days in time_points:
            # Paris定律增长因子
            growth_factor = 1.0 + self.paris_C * (t_days ** self.paris_m)
            
            # 应用低秩约束
            pred_dims = initial_dims * growth_factor
            
            # 各维度按基向量权重演化
            for i in range(3):
                dim_growth = np.sum(coeffs * basis[:, i])
                pred_dims[i] *= (1.0 + dim_growth * t_days / days)
            
            # 物理约束
            pred_dims[2] = min(pred_dims[2], 0.5)  # 深度最大50cm
            
            predictions.append(pred_dims)
        
        return time_points, np.array(predictions)
    
    def assess_risk(self, dimensions):
        """评估风险等级"""
        depth = dimensions[2]
        area = dimensions[0] * dimensions[1]
        
        if depth > 0.1 or area > 0.5:
            return 'critical'
        elif depth > 0.05 or area > 0.2:
            return 'high'
        elif depth > 0.02:
            return 'medium'
        else:
            return 'low'

# 创建模拟器
simulator = DefectEvolutionSimulator()

# 定义3个典型缺陷场景
scenarios = [
    {
        'name': '小型裂缝',
        'initial': np.array([0.3, 0.05, 0.01]),  # 30cm x 5cm x 1cm
        'material': 'asphalt',
        'type': 'crack'
    },
    {
        'name': '中型坑槽',
        'initial': np.array([0.4, 0.4, 0.05]),   # 40cm x 40cm x 5cm
        'material': 'asphalt',
        'type': 'pothole'
    },
    {
        'name': '混凝土裂缝',
        'initial': np.array([0.5, 0.1, 0.02]),   # 50cm x 10cm x 2cm
        'material': 'concrete',
        'type': 'crack'
    }
]

# 创建可视化
fig = plt.figure(figsize=(16, 12))
fig.suptitle('世界模型：路面缺陷演化预测\n低秩动力学 + Paris定律', 
             fontsize=18, fontweight='bold', y=0.98)

output_dir = Path('world_model_demo')
output_dir.mkdir(exist_ok=True)

# 为每个场景创建子图
for idx, scenario in enumerate(scenarios, 1):
    print(f"\n预测场景 {idx}: {scenario['name']}")
    print(f"  初始尺寸: {scenario['initial']*100} cm")
    print(f"  材质: {scenario['material']}")
    
    # 预测演化
    time_points, predictions = simulator.predict_evolution(
        scenario['initial'], 
        scenario['material']
    )
    
    # 评估风险
    risks = [simulator.assess_risk(pred) for pred in predictions]
    
    # 输出预测结果
    print(f"\n  预测结果:")
    for t, pred, risk in zip(time_points, predictions, risks):
        print(f"    第{int(t):2d}天: 深度 {pred[2]*100:.2f}cm, 面积 {pred[0]*pred[1]*10000:.1f}cm², 风险: {risk}")
    
    # 子图1: 三维演化
    ax1 = fig.add_subplot(3, 3, idx*3-2, projection='3d')
    ax1.set_title(f'{scenario["name"]} - 三维演化', fontsize=12, pad=10)
    
    # 绘制演化轨迹
    ax1.plot(predictions[:, 0]*100, predictions[:, 1]*100, predictions[:, 2]*100, 
             'o-', linewidth=2, markersize=8, label='演化轨迹')
    ax1.scatter(predictions[0, 0]*100, predictions[0, 1]*100, predictions[0, 2]*100,
                color='green', s=150, marker='*', label='初始状态', zorder=5)
    ax1.scatter(predictions[-1, 0]*100, predictions[-1, 1]*100, predictions[-1, 2]*100,
                color='red', s=150, marker='X', label='90天后', zorder=5)
    
    ax1.set_xlabel('长度 (cm)', fontsize=10)
    ax1.set_ylabel('宽度 (cm)', fontsize=10)
    ax1.set_zlabel('深度 (cm)', fontsize=10)
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # 子图2: 深度随时间变化
    ax2 = fig.add_subplot(3, 3, idx*3-1)
    ax2.set_title(f'{scenario["name"]} - 深度演化曲线', fontsize=12, pad=10)
    
    ax2.plot(time_points, predictions[:, 2]*100, 'o-', linewidth=2.5, 
             markersize=8, color='#E74C3C', label='深度')
    ax2.axhline(y=5, color='orange', linestyle='--', linewidth=1.5, label='高风险阈值(5cm)')
    ax2.axhline(y=10, color='red', linestyle='--', linewidth=1.5, label='危险阈值(10cm)')
    ax2.fill_between(time_points, 0, predictions[:, 2]*100, alpha=0.2, color='#E74C3C')
    
    ax2.set_xlabel('时间 (天)', fontsize=11)
    ax2.set_ylabel('深度 (cm)', fontsize=11)
    ax2.legend(fontsize=9, loc='upper left')
    ax2.grid(True, alpha=0.3, linestyle=':')
    ax2.set_xlim(0, 90)
    
    # 子图3: 风险等级变化
    ax3 = fig.add_subplot(3, 3, idx*3)
    ax3.set_title(f'{scenario["name"]} - 风险等级演化', fontsize=12, pad=10)
    
    risk_colors = {'low': '#27AE60', 'medium': '#F39C12', 'high': '#E67E22', 'critical': '#C0392B'}
    risk_levels_numeric = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
    
    risk_values = [risk_levels_numeric[r] for r in risks]
    colors = [risk_colors[r] for r in risks]
    
    bars = ax3.bar(time_points, risk_values, width=10, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    ax3.set_xlabel('时间 (天)', fontsize=11)
    ax3.set_ylabel('风险等级', fontsize=11)
    ax3.set_yticks([1, 2, 3, 4])
    ax3.set_yticklabels(['Low', 'Medium', 'High', 'Critical'])
    ax3.set_xlim(-5, 95)
    ax3.grid(True, axis='y', alpha=0.3, linestyle=':')
    
    # 添加推荐养护时间
    for i, (t, risk) in enumerate(zip(time_points, risks)):
        if risk in ['high', 'critical'] and (i == 0 or risks[i-1] not in ['high', 'critical']):
            ax3.axvline(x=t, color='red', linestyle='--', linewidth=2, alpha=0.7)
            ax3.text(t, 4.3, f'推荐养护\n第{int(t)}天', ha='center', fontsize=9, 
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
            break

plt.tight_layout(rect=[0, 0.02, 1, 0.96])

# 保存图片
output_path = output_dir / 'world_model_evolution_demo.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
print(f"\n✅ 可视化已保存: {output_path}")

# 创建汇总报告
print("\n" + "="*70)
print("预测汇总")
print("="*70)

for idx, scenario in enumerate(scenarios, 1):
    time_points, predictions = simulator.predict_evolution(
        scenario['initial'], scenario['material']
    )
    risks = [simulator.assess_risk(pred) for pred in predictions]
    
    # 找到首次达到high风险的时间
    maintenance_day = None
    for t, risk in zip(time_points, risks):
        if risk in ['high', 'critical']:
            maintenance_day = int(t)
            break
    
    print(f"\n{scenario['name']}:")
    print(f"  初始: 深度 {scenario['initial'][2]*100:.1f}cm")
    print(f"  90天后: 深度 {predictions[-1][2]*100:.1f}cm")
    print(f"  增长率: {((predictions[-1][2]/scenario['initial'][2])-1)*100:.1f}%")
    print(f"  最终风险: {risks[-1]}")
    if maintenance_day:
        print(f"  推荐养护时间: 第 {maintenance_day} 天")
    else:
        print(f"  推荐养护时间: 90天后")

print("\n" + "="*70)
print("✅ 世界模型Demo完成!")
print(f"📊 查看可视化: {output_path}")
print("="*70)
