#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练YOLOv8路面缺陷检测模型
使用N-RDD2024数据集
"""
import sys
import io
from pathlib import Path

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("="*70)
print("YOLOv8路面缺陷检测模型训练")
print("数据集: N-RDD2024")
print("="*70)
print()

# 检查数据集
repo_dir = Path('Road-Damage-and-Defect-Recognition-Model')
if not repo_dir.exists():
    print("❌ 请先运行 keras_road_damage.py 克隆仓库")
    sys.exit(1)

print("✅ 仓库已存在")
print(f"   路径: {repo_dir}")

# 查找数据集文件
dataset_file = repo_dir / 'Compiled Dataset of N-RDD2024'
print(f"\n📦 数据集文件: {dataset_file}")

if dataset_file.exists():
    print("✅ 找到数据集文件")
    # 读取内容
    try:
        content = dataset_file.read_text(encoding='utf-8')
        print(f"\n数据集链接:")
        print(content[:500])
    except:
        pass
else:
    print("⚠️  数据集文件不存在")

print("\n" + "="*70)
print("📝 训练步骤说明")
print("="*70)

print("""
由于数据集通常很大（几GB），完整训练需要：
1. 下载N-RDD2024数据集（从Google Drive等）
2. 转换为YOLO格式（.txt标注文件）
3. 创建dataset.yaml配置
4. 运行训练（需要GPU，耗时数小时）

但是，我们可以使用以下方案快速演示：

方案A: 使用公开的预训练模型
- Roboflow Universe: 搜索 "road damage detection yolov8"
- 直接下载.pt文件

方案B: 使用小规模数据快速训练
- 下载少量样本（100-200张）
- 快速训练10-20个epoch
- 用于演示和验证

方案C: 模拟训练结果
- 创建训练脚本和配置
- 使用通用模型作为基础
- 展示训练流程
""")

print("\n💡 推荐方案: 下载预训练模型")
print("="*70)

# 创建数据集配置模板
yaml_content = """# N-RDD2024路面缺陷数据集配置
# 用于YOLOv8训练

path: ./datasets/n_rdd2024  # 数据集根目录
train: images/train  # 训练集
val: images/val      # 验证集
test: images/test    # 测试集（可选）

# 类别定义（RDD2020标准）
nc: 10  # 类别数量
names: ['D00', 'D10', 'D20', 'D30', 'D40', 'D50', 'D60', 'D70', 'D80', 'D90']

# 类别说明
# D00: 横向裂缝 (Transverse crack)
# D10: 纵向裂缝 (Longitudinal crack)  
# D20: 龟裂 (Alligator crack)
# D30: 边缘裂缝 (Edge crack)
# D40: 坑槽 (Pothole)
# D50: 修补区域 (Repair area)
# D60: 井盖破损 (Manhole cover)
# D70: 路面标线损坏 (Line marking damage)
# D80: 排水设施损坏 (Drainage damage)
# D90: 其他损坏 (Other damage)
"""

config_path = Path('models/n_rdd2024.yaml')
config_path.parent.mkdir(exist_ok=True)
config_path.write_text(yaml_content, encoding='utf-8')
print(f"\n✅ 已创建数据集配置: {config_path}")

# 创建训练脚本
train_script = """#!/usr/bin/env python3
\"\"\"
YOLOv8路面缺陷检测训练脚本
\"\"\"
from ultralytics import YOLO
import torch

print("="*70)
print("开始训练YOLOv8路面缺陷检测模型")
print("="*70)

# 检查GPU
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"\\n使用设备: {device}")

# 加载预训练模型
print("\\n加载预训练模型...")
model = YOLO('yolov8n.pt')  # nano版本，快速训练

# 训练参数
print("\\n训练参数:")
params = {
    'data': 'models/n_rdd2024.yaml',
    'epochs': 50,                # 完整训练建议100+
    'imgsz': 640,
    'batch': 16,                 # 根据显存调整
    'device': device,
    'project': 'road_damage_training',
    'name': 'yolov8n_nrdd2024',
    'patience': 20,
    'save': True,
    'save_period': 10,
    
    # 数据增强
    'hsv_h': 0.015,
    'hsv_s': 0.7,
    'hsv_v': 0.4,
    'degrees': 10.0,
    'translate': 0.1,
    'scale': 0.5,
    'mosaic': 1.0,
}

for key, value in params.items():
    print(f"  {key}: {value}")

# 开始训练
print("\\n开始训练...")
print("(这可能需要数小时，取决于GPU性能)")

try:
    results = model.train(**params)
    
    print("\\n训练完成！")
    print(f"最佳模型: road_damage_training/yolov8n_nrdd2024/weights/best.pt")
    
    # 验证
    metrics = model.val()
    print(f"\\nmAP50: {metrics.box.map50:.3f}")
    print(f"mAP50-95: {metrics.box.map:.3f}")
    
    # 导出模型
    print("\\n导出模型...")
    model.export(format='onnx')
    print("✅ 模型已导出为ONNX格式")
    
except Exception as e:
    print(f"\\n❌ 训练失败: {e}")
    print("\\n请确保:")
    print("1. 数据集已下载到正确位置")
    print("2. dataset.yaml配置正确")
    print("3. 有足够的磁盘空间和内存")

print("\\n="*70)
print("训练脚本执行完成")
print("="*70)
\"\"\"

train_script_path = Path('train_road_damage_yolov8.py')
train_script_path.write_text(train_script, encoding='utf-8')
print(f"✅ 已创建训练脚本: {train_script_path}")

print("\n" + "="*70)
print("📋 后续步骤")
print("="*70)
print("""
1. 下载数据集
   - 查看 Road-Damage-and-Defect-Recognition-Model/Compiled Dataset of N-RDD2024
   - 从Google Drive下载数据集
   - 解压到 datasets/n_rdd2024/

2. 准备数据（如果需要转换格式）
   - 确保图片在 images/train, images/val 目录
   - 标注文件在 labels/train, labels/val 目录
   - 每个图片对应一个.txt标注文件

3. 运行训练
   python train_road_damage_yolov8.py

4. 或直接使用预训练模型
   - 下载: https://universe.roboflow.com/
   - 搜索: "road damage detection yolov8"
   - 下载.pt文件到 models/road_damage_yolov8.pt
""")

print("\n✅ 准备工作完成!")
print(f"   配置文件: {config_path}")
print(f"   训练脚本: {train_script_path}")
