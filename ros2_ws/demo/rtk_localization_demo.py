#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTK定位系统与ROS2数据流可视化
展示GPS/RTK定位 + 多传感器融合的完整流程
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib
matplotlib.use('Agg')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

print("="*70)
print("RTK定位系统与ROS2数据流可视化")
print("="*70)

# 创建图形
fig = plt.figure(figsize=(18, 14))
fig.suptitle('校园道路巡检系统 - RTK定位与ROS2数据流', fontsize=20, fontweight='bold', y=0.98)

# ============ 图1: RTK定位原理 ============
ax1 = plt.subplot(2, 2, 1)
ax1.set_xlim(0, 10)
ax1.set_ylim(0, 10)
ax1.axis('off')
ax1.set_title('RTK-GPS定位原理', fontsize=14, fontweight='bold', pad=20)

# 基站
base_station = mpatches.FancyBboxPatch((0.5, 7), 1.5, 1.5, 
    boxstyle="round,pad=0.1", edgecolor='red', facecolor='#FFE5E5', linewidth=3)
ax1.add_patch(base_station)
ax1.text(1.25, 7.75, 'RTK基站\n(已知精确坐标)', ha='center', va='center', 
        fontsize=10, fontweight='bold')

# 卫星
satellites = [(2, 9), (4, 9.5), (6, 9), (8, 9.3)]
for i, (x, y) in enumerate(satellites):
    sat = mpatches.Circle((x, y), 0.3, color='#FFD700', ec='orange', linewidth=2)
    ax1.add_patch(sat)
    ax1.text(x, y, f'卫星{i+1}', ha='center', va='center', fontsize=8)

# 移动站（机器人）
robot = mpatches.FancyBboxPatch((4, 2), 2, 1.5,
    boxstyle="round,pad=0.1", edgecolor='blue', facecolor='#E5F2FF', linewidth=3)
ax1.add_patch(robot)
ax1.text(5, 2.75, '移动站\n(巡检机器人)', ha='center', va='center',
        fontsize=10, fontweight='bold', color='blue')

# 信号线
# 卫星到基站
for x, y in satellites[:2]:
    ax1.plot([x, 1.25], [y, 8.5], 'r--', linewidth=1.5, alpha=0.6)
ax1.text(2, 8.8, '卫星信号', fontsize=9, color='red')

# 卫星到机器人
for x, y in satellites[2:]:
    ax1.plot([x, 5], [y, 3.5], 'b--', linewidth=1.5, alpha=0.6)
ax1.text(6.5, 6, '卫星信号', fontsize=9, color='blue')

# RTK差分信号
arrow1 = FancyArrowPatch((1.25, 7), (4.5, 3.5),
    arrowstyle='->', mutation_scale=30, linewidth=3, color='green')
ax1.add_patch(arrow1)
ax1.text(2.5, 5, 'RTK差分修正\n(厘米级精度)', fontsize=9, color='green',
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

# 精度说明
ax1.text(5, 0.8, '定位精度: ±2cm (水平) / ±5cm (垂直)', 
        ha='center', fontsize=10, 
        bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

# ============ 图2: 传感器融合架构 ============
ax2 = plt.subplot(2, 2, 2)
ax2.set_xlim(0, 10)
ax2.set_ylim(0, 10)
ax2.axis('off')
ax2.set_title('多传感器融合定位架构', fontsize=14, fontweight='bold', pad=20)

# 传感器层
sensors_y = 8.5
sensors = [
    ('RTK-GPS\n±2cm', 1, '#FFE5E5'),
    ('IMU\n姿态', 3, '#E5FFE5'),
    ('轮式里程计\n相对位移', 5, '#E5E5FF'),
    ('Livox雷达\n点云匹配', 7.5, '#FFE5FF')
]

for name, x, color in sensors:
    box = mpatches.FancyBboxPatch((x-0.6, sensors_y-0.4), 1.2, 0.8,
        boxstyle="round,pad=0.05", edgecolor='black', facecolor=color, linewidth=2)
    ax2.add_patch(box)
    ax2.text(x, sensors_y, name, ha='center', va='center', fontsize=8, fontweight='bold')

# 融合层
fusion_y = 6
fusion_box = mpatches.FancyBboxPatch((2, fusion_y-0.5), 6, 1,
    boxstyle="round,pad=0.1", edgecolor='red', facecolor='#FFF5E5', linewidth=3)
ax2.add_patch(fusion_box)
ax2.text(5, fusion_y, '扩展卡尔曼滤波 (EKF)\n多传感器融合', 
        ha='center', va='center', fontsize=11, fontweight='bold')

# 箭头连接
for name, x, color in sensors:
    arrow = FancyArrowPatch((x, sensors_y-0.4), (x, fusion_y+0.5),
        arrowstyle='->', mutation_scale=20, linewidth=2, color='gray')
    ax2.add_patch(arrow)

# 定位输出
output_y = 4
output_box = mpatches.FancyBboxPatch((2, output_y-0.5), 6, 1,
    boxstyle="round,pad=0.1", edgecolor='blue', facecolor='#E5F2FF', linewidth=3)
ax2.add_patch(output_box)
ax2.text(5, output_y, '融合定位输出\n位置(x,y,z) + 姿态(roll,pitch,yaw)', 
        ha='center', va='center', fontsize=10, fontweight='bold', color='blue')

arrow_fusion = FancyArrowPatch((5, fusion_y-0.5), (5, output_y+0.5),
    arrowstyle='->', mutation_scale=25, linewidth=3, color='red')
ax2.add_patch(arrow_fusion)

# 地图层
map_y = 2
map_box = mpatches.FancyBboxPatch((1, map_y-0.5), 8, 1,
    boxstyle="round,pad=0.1", edgecolor='green', facecolor='#E5FFE5', linewidth=3)
ax2.add_patch(map_box)
ax2.text(5, map_y, '动态路面地图 + 缺陷标注\n实时更新机器人位置与检测结果', 
        ha='center', va='center', fontsize=10, fontweight='bold', color='green')

arrow_map = FancyArrowPatch((5, output_y-0.5), (5, map_y+0.5),
    arrowstyle='->', mutation_scale=25, linewidth=3, color='blue')
ax2.add_patch(arrow_map)

# ============ 图3: ROS2话题数据流 ============
ax3 = plt.subplot(2, 1, 2)
ax3.set_xlim(0, 14)
ax3.set_ylim(0, 10)
ax3.axis('off')
ax3.set_title('ROS2话题数据流', fontsize=16, fontweight='bold', pad=20)

# 节点定义
nodes = {
    'rtk': {'pos': (1, 8), 'name': 'RTK驱动节点', 'color': '#FFE5E5'},
    'imu': {'pos': (1, 6), 'name': 'IMU驱动节点', 'color': '#E5FFE5'},
    'odom': {'pos': (1, 4), 'name': '里程计节点', 'color': '#E5E5FF'},
    'lidar': {'pos': (1, 2), 'name': 'Livox雷达节点', 'color': '#FFE5FF'},
    
    'localization': {'pos': (5, 5), 'name': 'EKF定位融合', 'color': '#FFF5E5'},
    
    'ground_seg': {'pos': (8, 7), 'name': '地面分割', 'color': '#E5F5FF'},
    'lidar_detect': {'pos': (8, 5), 'name': '激光检测', 'color': '#F5E5FF'},
    'vision_detect': {'pos': (8, 3), 'name': '视觉检测', 'color': '#FFFFE5'},
    
    'fusion': {'pos': (11, 5), 'name': '传感器融合', 'color': '#FFE5E5'},
    
    'world_model': {'pos': (11, 7), 'name': '世界模型', 'color': '#E5FFE5'},
    'roadmap': {'pos': (11, 3), 'name': '动态地图', 'color': '#E5E5FF'},
}

# 绘制节点
for key, node in nodes.items():
    x, y = node['pos']
    box = mpatches.FancyBboxPatch((x-0.6, y-0.35), 1.2, 0.7,
        boxstyle="round,pad=0.05", edgecolor='black', 
        facecolor=node['color'], linewidth=2)
    ax3.add_patch(box)
    ax3.text(x, y, node['name'], ha='center', va='center', 
            fontsize=9, fontweight='bold')

# 话题连接
topics = [
    # 驱动层 -> 定位融合
    ('rtk', 'localization', '/gnss/fix\n(GPS坐标)', 'blue'),
    ('imu', 'localization', '/imu/data\n(姿态)', 'green'),
    ('odom', 'localization', '/odom\n(里程)', 'orange'),
    
    # 定位融合 -> 感知层
    ('localization', 'ground_seg', '/localization/pose', 'red'),
    ('localization', 'lidar_detect', '/localization/pose', 'red'),
    ('localization', 'vision_detect', '/localization/pose', 'red'),
    
    # 雷达数据流
    ('lidar', 'ground_seg', '/livox/lidar', 'purple'),
    ('ground_seg', 'lidar_detect', '/ground/segmented', 'purple'),
    
    # 检测 -> 融合
    ('lidar_detect', 'fusion', '/lidar/defects', 'brown'),
    ('vision_detect', 'fusion', '/vision/defects', 'brown'),
    
    # 融合 -> 算法层
    ('fusion', 'world_model', '/fused_defects', 'red'),
    ('fusion', 'roadmap', '/fused_defects', 'red'),
    
    # 算法层输出
    ('world_model', 'roadmap', '/prediction/evolution', 'blue'),
]

# 绘制箭头和话题标签
for i, (src, dst, topic, color) in enumerate(topics):
    src_pos = nodes[src]['pos']
    dst_pos = nodes[dst]['pos']
    
    # 计算箭头位置
    dx = dst_pos[0] - src_pos[0]
    dy = dst_pos[1] - src_pos[1]
    
    # 箭头样式
    arrow = FancyArrowPatch(
        (src_pos[0]+0.6, src_pos[1]), 
        (dst_pos[0]-0.6, dst_pos[1]),
        arrowstyle='->', mutation_scale=15, linewidth=1.5, 
        color=color, alpha=0.7,
        connectionstyle="arc3,rad=0.1" if abs(dy) < 0.5 else "arc3,rad=0"
    )
    ax3.add_patch(arrow)
    
    # 话题标签
    mid_x = (src_pos[0] + dst_pos[0]) / 2
    mid_y = (src_pos[1] + dst_pos[1]) / 2 + 0.2
    ax3.text(mid_x, mid_y, topic, fontsize=7, ha='center',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', 
                     edgecolor=color, alpha=0.8))

# 图例
legend_elements = [
    mpatches.Patch(facecolor='#FFE5E5', edgecolor='black', label='驱动层'),
    mpatches.Patch(facecolor='#FFF5E5', edgecolor='black', label='定位层'),
    mpatches.Patch(facecolor='#E5F5FF', edgecolor='black', label='感知层'),
    mpatches.Patch(facecolor='#FFE5E5', edgecolor='black', label='融合层'),
    mpatches.Patch(facecolor='#E5FFE5', edgecolor='black', label='算法层'),
]
ax3.legend(handles=legend_elements, loc='upper right', fontsize=9)

# 关键话题说明
info_text = """
关键ROS2话题:
• /gnss/fix (sensor_msgs/NavSatFix) - GPS坐标 (WGS84)
• /imu/data (sensor_msgs/Imu) - 9轴IMU数据
• /odom (nav_msgs/Odometry) - 轮式里程计
• /livox/lidar (sensor_msgs/PointCloud2) - 点云数据
• /localization/pose (geometry_msgs/PoseStamped) - 融合定位
• /fused_defects (cri_msgs/DefectArray) - 融合缺陷
• /prediction/evolution (cri_msgs/DefectPrediction) - 演化预测
"""
ax3.text(0.5, 0.5, info_text, fontsize=8, family='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

plt.tight_layout(rect=[0, 0.02, 1, 0.97])

# 保存
output_path = 'world_model_demo/rtk_localization_ros2_flow.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
print(f"\n✅ RTK定位与ROS2数据流图已保存: {output_path}")

plt.close()

print("\n" + "="*70)
print("RTK定位系统说明")
print("="*70)
print("""
1. RTK-GPS定位原理：
   - 基站：固定位置，已知精确坐标
   - 移动站：机器人上的GPS接收机
   - 差分修正：消除大气延迟等误差
   - 精度：水平±2cm，垂直±5cm

2. 多传感器融合：
   - RTK-GPS：提供全局绝对位置
   - IMU：提供姿态和短期位移
   - 轮式里程计：提供连续相对位移
   - Livox雷达：点云匹配提供局部定位
   - EKF融合：综合所有传感器，输出最优估计

3. 地图定位：
   - 全局坐标系：WGS84 (GPS坐标)
   - 局部坐标系：东北天 (ENU)
   - 地图坐标系：栅格地图 (0.5m分辨率)
   - 缺陷标注：每个缺陷记录GPS坐标和地图栅格

4. ROS2数据流：
   - 10Hz：RTK-GPS数据更新
   - 100Hz：IMU数据更新
   - 50Hz：里程计数据
   - 10Hz：雷达点云
   - 20Hz：融合定位输出
   - 5Hz：缺陷检测与地图更新

5. 实时性保证：
   - 时间同步：所有传感器时间戳对齐
   - 消息缓存：存储历史数据用于插值
   - 优先级调度：定位>检测>预测
""")

print("\n✅ 可视化完成！查看图片: " + output_path)
print("="*70)
