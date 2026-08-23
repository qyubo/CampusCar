#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库与UE5地图集成架构可视化
展示完整的数据流：检测→分类→定位→数据库→UE5地图
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import matplotlib
matplotlib.use('Agg')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

print("="*70)
print("数据库与UE5地图集成架构可视化")
print("="*70)

# 创建图形
fig = plt.figure(figsize=(20, 12))
fig.suptitle('缺陷检测→分类→定位→数据库→UE5地图 完整架构', 
             fontsize=18, fontweight='bold', y=0.98)

ax = plt.subplot(111)
ax.set_xlim(0, 20)
ax.set_ylim(0, 12)
ax.axis('off')

# 颜色定义
colors = {
    'detection': '#FFE5E5',
    'classification': '#E5FFE5',
    'localization': '#E5E5FF',
    'database': '#FFE5FF',
    'ue5': '#FFFFE5',
}

# ========== 第1层：检测识别 ==========
y_detect = 10
detect_box = FancyBboxPatch((0.5, y_detect-0.4), 3, 0.8,
    boxstyle="round,pad=0.1", edgecolor='red', facecolor=colors['detection'], linewidth=3)
ax.add_patch(detect_box)
ax.text(2, y_detect, '① 检测识别\nYOLOv8 + Livox', ha='center', va='center',
        fontsize=11, fontweight='bold')

# ========== 第2层：分类标注 ==========
y_class = 8
class_box = FancyBboxPatch((0.5, y_class-0.4), 3, 0.8,
    boxstyle="round,pad=0.1", edgecolor='green', facecolor=colors['classification'], linewidth=3)
ax.add_patch(class_box)
ax.text(2, y_class, '② 分类标注\n类型+严重程度', ha='center', va='center',
        fontsize=11, fontweight='bold')

arrow1 = FancyArrowPatch((2, y_detect-0.4), (2, y_class+0.4),
    arrowstyle='->', mutation_scale=30, linewidth=3, color='black')
ax.add_patch(arrow1)

# 分类详情
class_detail = """
类型分类:
• crack (裂缝)
  - D00 横向
  - D10 纵向  
  - D20 龟裂
• pothole (坑槽)
• depression (沉降)

严重程度:
• low (轻微)
• medium (中等)
• high (严重)
• critical (危险)
"""
ax.text(4.5, y_class, class_detail, fontsize=8, family='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8),
        va='center')

# ========== 第3层：GPS定位打包 ==========
y_gps = 6
gps_box = FancyBboxPatch((0.5, y_gps-0.4), 3, 0.8,
    boxstyle="round,pad=0.1", edgecolor='blue', facecolor=colors['localization'], linewidth=3)
ax.add_patch(gps_box)
ax.text(2, y_gps, '③ GPS定位打包\nRTK ±2cm', ha='center', va='center',
        fontsize=11, fontweight='bold')

arrow2 = FancyArrowPatch((2, y_class-0.4), (2, y_gps+0.4),
    arrowstyle='->', mutation_scale=30, linewidth=3, color='black')
ax.add_patch(arrow2)

# GPS详情
gps_detail = """
坐标系统:
• GPS (WGS84)
  - 纬度 latitude
  - 经度 longitude
  - 海拔 altitude

• UTM投影
  - 东坐标 easting
  - 北坐标 northing
  - 分区 zone

• 校园局部坐标
  - X (东) Y (北) Z (高)
"""
ax.text(4.5, y_gps, gps_detail, fontsize=8, family='monospace',
        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
        va='center')

# ========== 第4层：数据库存储 ==========
y_db = 4
db_box = FancyBboxPatch((0.5, y_db-0.6), 3, 1.2,
    boxstyle="round,pad=0.1", edgecolor='purple', facecolor=colors['database'], linewidth=3)
ax.add_patch(db_box)
ax.text(2, y_db+0.2, '④ 数据库存储', ha='center', va='center',
        fontsize=11, fontweight='bold')
ax.text(2, y_db-0.2, 'PostgreSQL + PostGIS', ha='center', va='center',
        fontsize=9, style='italic')

arrow3 = FancyArrowPatch((2, y_gps-0.4), (2, y_db+0.6),
    arrowstyle='->', mutation_scale=30, linewidth=3, color='black')
ax.add_patch(arrow3)

# 数据库表结构
db_tables = """
主要表结构:

defects (缺陷表)
├─ id, defect_id
├─ type, sub_type, severity
├─ dimensions (长宽高)
├─ GPS坐标 (lat, lon, alt)
├─ UTM坐标
├─ 局部坐标 (x, y, z)
├─ 姿态 (roll, pitch, yaw)
├─ 时间戳, 机器人ID
└─ 状态, 优先级

defect_evolution (演化表)
├─ 预测数据
└─ 实际观测

maintenance_records (养护表)
├─ 养护类型
└─ 时间与成本
"""
ax.text(4.5, y_db, db_tables, fontsize=7, family='monospace',
        bbox=dict(boxstyle='round', facecolor='lavender', alpha=0.8),
        va='center')

# ========== 第5层：UE5地图显示 ==========
y_ue5 = 1.5
ue5_box = FancyBboxPatch((0.5, y_ue5-0.6), 3, 1.2,
    boxstyle="round,pad=0.1", edgecolor='orange', facecolor=colors['ue5'], linewidth=3)
ax.add_patch(ue5_box)
ax.text(2, y_ue5+0.2, '⑤ UE5地图显示', ha='center', va='center',
        fontsize=11, fontweight='bold')
ax.text(2, y_ue5-0.2, '虚幻引擎5', ha='center', va='center',
        fontsize=9, style='italic')

# 两条路径
# 路径1: 实时WebSocket
arrow4a = FancyArrowPatch((3.5, y_db), (8, y_db),
    arrowstyle='->', mutation_scale=25, linewidth=2.5, color='green',
    connectionstyle="arc3,rad=0.3")
ax.add_patch(arrow4a)
ax.text(5.5, y_db+0.8, '实时推送\nWebSocket', ha='center', fontsize=9,
        color='green', fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

# rosbridge
bridge_box = FancyBboxPatch((8, y_db-0.3), 1.5, 0.6,
    boxstyle="round,pad=0.05", edgecolor='green', facecolor='lightgreen', linewidth=2)
ax.add_patch(bridge_box)
ax.text(8.75, y_db, 'rosbridge\nWS:9090', ha='center', va='center',
        fontsize=8, fontweight='bold')

arrow4b = FancyArrowPatch((9.5, y_db), (12, y_ue5+0.6),
    arrowstyle='->', mutation_scale=25, linewidth=2.5, color='green',
    connectionstyle="arc3,rad=-0.2")
ax.add_patch(arrow4b)

# 路径2: REST API查询
arrow5a = FancyArrowPatch((3.5, y_db-0.3), (8, y_db-0.3),
    arrowstyle='<->', mutation_scale=25, linewidth=2.5, color='blue',
    connectionstyle="arc3,rad=-0.3")
ax.add_patch(arrow5a)
ax.text(5.5, y_db-1.2, '批量查询\nREST API', ha='center', fontsize=9,
        color='blue', fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

# REST API
api_box = FancyBboxPatch((8, y_db-0.9), 1.5, 0.6,
    boxstyle="round,pad=0.05", edgecolor='blue', facecolor='lightblue', linewidth=2)
ax.add_patch(api_box)
ax.text(8.75, y_db-0.6, 'FastAPI\n/api/defects', ha='center', va='center',
        fontsize=8, fontweight='bold')

arrow5b = FancyArrowPatch((9.5, y_db-0.6), (12, y_ue5),
    arrowstyle='<->', mutation_scale=25, linewidth=2.5, color='blue',
    connectionstyle="arc3,rad=0.2")
ax.add_patch(arrow5b)

# UE5详细功能
ue5_detail = """
UE5功能:

1. 坐标转换
   GPS → UE5世界坐标

2. 缺陷标记
   • 根据类型选择图标
   • 根据严重程度着色
     - Low: 绿色
     - Medium: 黄色
     - High: 橙色
     - Critical: 红色

3. 交互功能
   • 点击查看详情
   • 查询周边缺陷
   • 显示演化预测
   • 安排养护

4. 可视化
   • 热力图
   • 时间轴
   • 统计图表
"""
ax.text(12.5, y_ue5, ue5_detail, fontsize=8, family='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8),
        va='center')

# ========== 右侧：数据包格式 ==========
data_package = """
完整数据包示例:

{
  "defect_id": "D001_20260702_001",
  "type": "crack",
  "sub_type": "D00",
  "confidence": 0.87,
  "severity": "medium",
  
  "dimensions": {
    "length": 0.5,
    "width": 0.1,
    "depth": 0.02
  },
  
  "location": {
    "gps": {
      "latitude": 31.026470,
      "longitude": 121.434550,
      "altitude": 5.23
    },
    "utm": {
      "easting": 326543.21,
      "northing": 3436789.45,
      "zone": "51N"
    },
    "local": {
      "x": 123.45,
      "y": 456.78,
      "z": 5.23
    }
  },
  
  "pose": {
    "roll": 0.01,
    "pitch": 0.02,
    "yaw": 1.57
  },
  
  "metadata": {
    "timestamp": "2026-07-02T10:30:45Z",
    "robot_id": "robot_001",
    "image_path": "/data/images/...",
    "pointcloud_path": "/data/pcd/..."
  }
}
"""
ax.text(16.5, 6, data_package, fontsize=7, family='monospace',
        bbox=dict(boxstyle='round', facecolor='white', 
                 edgecolor='gray', linewidth=2, alpha=0.9),
        va='center')

# ========== 底部：实施步骤 ==========
steps = """
实施步骤:
1️⃣ 数据库搭建 (1-2天)    PostgreSQL + PostGIS + 表结构
2️⃣ ROS2集成 (1天)        创建完整消息类型 + 发布节点
3️⃣ UE5基础显示 (2-3天)   坐标转换 + 标记显示 + WebSocket接收
4️⃣ 交互功能 (2天)        点击交互 + 详情面板 + 查询功能
5️⃣ 优化测试 (1天)        性能优化 + LOD + 批量加载
"""
ax.text(10, 0.3, steps, fontsize=9, fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))

plt.tight_layout()

# 保存
output_path = 'world_model_demo/database_ue5_architecture.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
print(f"\n✅ 架构图已保存: {output_path}")

plt.close()

print("\n" + "="*70)
print("核心要点总结")
print("="*70)
print("""
1. 完整数据流
   检测 → 分类 → 定位 → 数据库 → UE5
   
2. 数据包结构
   - 缺陷信息: 类型、严重程度、尺寸
   - GPS定位: 三种坐标系（GPS/UTM/局部）
   - 元数据: 时间戳、机器人ID、文件路径
   
3. 数据库设计
   - defects: 主表，存储所有缺陷
   - defect_evolution: 演化预测历史
   - maintenance_records: 养护记录
   - PostGIS空间索引: 快速空间查询
   
4. UE5集成方式
   - 实时: WebSocket推送新检测
   - 批量: REST API查询历史
   - 显示: 坐标转换 + 3D标记
   - 交互: 点击详情 + 查询功能
   
5. 坐标转换
   GPS (WGS84) → UTM投影 → 局部ENU → UE5世界坐标
   关键: 校准校园原点GPS坐标
   
6. 技术栈
   - 数据库: PostgreSQL + PostGIS
   - API: FastAPI (Python)
   - 通信: rosbridge + WebSocket
   - 可视化: UE5蓝图 + C++
""")

print("\n✅ 架构可视化完成！")
print(f"📊 查看图片: {output_path}")
print(f"📖 查看文档: docs/DATABASE_UE5_INTEGRATION.md")
print("="*70)
