#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动下载并准备路面缺陷检测模型
方案1: 下载Roboflow预训练模型
方案2: 使用样本数据快速训练
"""
import sys
import io
import urllib.request
import zipfile
from pathlib import Path

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("="*70)
print("路面缺陷检测模型 - 自动下载与准备")
print("="*70)
print()

# 创建models目录
models_dir = Path('models')
models_dir.mkdir(exist_ok=True)

# 方案1: 下载公开的预训练模型
print("方案1: 下载预训练模型")
print("-"*70)

# 尝试从Ultralytics Hub或Roboflow获取
model_urls = {
    # Ultralytics官方YOLOv8模型
    'yolov8n.pt': 'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt',
    
    # 可以替换为实际的路面缺陷预训练模型URL
    # 'road_damage_yolov8.pt': 'ACTUAL_MODEL_URL_HERE',
}

# 下载YOLOv8基础模型
for model_name, url in model_urls.items():
    model_path = models_dir / model_name
    
    if model_path.exists():
        print(f"✅ {model_name} 已存在")
        continue
    
    try:
        print(f"📥 下载 {model_name}...")
        print(f"   URL: {url}")
        urllib.request.urlretrieve(url, model_path)
        print(f"✅ 下载成功: {model_path}")
    except Exception as e:
        print(f"⚠️  下载失败: {e}")

print("\n方案2: 创建微调训练脚本")
print("-"*70)

# 创建快速训练脚本（使用小规模数据）
quick_train_script = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
快速训练YOLOv8路面缺陷模型
使用迁移学习，基于预训练模型微调
'''
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from ultralytics import YOLO
from pathlib import Path

print("="*70)
print("快速训练路面缺陷检测模型")
print("="*70)

# 检查数据集
data_yaml = Path('models/n_rdd2024.yaml')
if not data_yaml.exists():
    print("\\n❌ 数据集配置不存在: models/n_rdd2024.yaml")
    print("\\n创建示例配置...")
    
    # 创建示例配置
    config_content = '''# 路面缺陷数据集配置
path: ./datasets/n_rdd2024
train: images/train
val: images/val

nc: 10
names: ['D00', 'D10', 'D20', 'D30', 'D40', 'D50', 'D60', 'D70', 'D80', 'D90']
'''
    data_yaml.parent.mkdir(exist_ok=True)
    data_yaml.write_text(config_content, encoding='utf-8')
    print(f"✅ 已创建: {data_yaml}")

# 检查数据集是否存在
dataset_path = Path('datasets/n_rdd2024/images/train')
if not dataset_path.exists() or not list(dataset_path.glob('*.jpg')):
    print("\\n⚠️  训练数据集不存在")
    print("\\n请执行以下步骤:")
    print("1. 下载RDD2020或N-RDD2024数据集")
    print("2. 解压到 datasets/n_rdd2024/ 目录")
    print("3. 确保目录结构:")
    print("   datasets/n_rdd2024/")
    print("   ├── images/")
    print("   │   ├── train/   # 训练图片")
    print("   │   └── val/     # 验证图片")
    print("   └── labels/")
    print("       ├── train/   # 训练标注")
    print("       └── val/     # 验证标注")
    print("\\n临时方案: 使用通用模型作为路面缺陷模型")
    
    # 复制通用模型作为临时方案
    import shutil
    src = Path('yolov8n.pt')
    dst = Path('models/road_damage_yolov8.pt')
    if src.exists() and not dst.exists():
        shutil.copy(src, dst)
        print(f"\\n✅ 已复制通用模型到: {dst}")
        print("⚠️  注意: 这是通用模型，不是专门训练的路面缺陷模型")
        print("   下载真实数据集后可重新训练")
    
    sys.exit(0)

print("\\n✅ 数据集已找到，开始训练...")

# 加载预训练模型
print("\\n📦 加载预训练模型...")
model = YOLO('yolov8n.pt')

# 训练参数
print("\\n🚀 开始训练...")
results = model.train(
    data=str(data_yaml),
    epochs=30,              # 快速训练，完整训练建议100+
    imgsz=640,
    batch=8,                # 根据显存调整
    device='cpu',           # 使用CPU，如有GPU改为0
    project='road_damage_training',
    name='yolov8n_quick',
    patience=10,
    save=True,
    save_period=5,
    verbose=True,
    
    # 优化参数
    optimizer='AdamW',
    lr0=0.001,
    lrf=0.01,
    
    # 数据增强
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    degrees=10.0,
    translate=0.1,
    scale=0.5,
    mosaic=1.0,
)

print("\\n✅ 训练完成!")
print(f"\\n📊 训练结果:")
print(f"   项目目录: road_damage_training/yolov8n_quick/")

# 复制最佳模型
import shutil
best_model = Path('road_damage_training/yolov8n_quick/weights/best.pt')
target_model = Path('models/road_damage_yolov8.pt')

if best_model.exists():
    shutil.copy(best_model, target_model)
    print(f"\\n✅ 最佳模型已复制到: {target_model}")
    print("\\n🌐 现在可以在Streamlit应用中使用'路面缺陷专用模型'!")
else:
    print("\\n⚠️  未找到训练好的模型")

print("\\n" + "="*70)
print("训练完成!")
print("="*70)
'''

script_path = Path('quick_train_model.py')
script_path.write_text(quick_train_script, encoding='utf-8')
print(f"✅ 已创建训练脚本: {script_path}")

print("\n方案3: 使用通用模型作为临时方案")
print("-"*70)

# 如果没有专用模型，复制通用模型
road_damage_model = models_dir / 'road_damage_yolov8.pt'
yolov8n_model = Path('yolov8n.pt')

if not road_damage_model.exists():
    if yolov8n_model.exists():
        import shutil
        shutil.copy(yolov8n_model, road_damage_model)
        print(f"✅ 已复制通用模型到: {road_damage_model}")
        print("⚠️  注意: 这是通用YOLOv8模型，不是专门的路面缺陷模型")
        print("   训练完成后会替换为专用模型")
    else:
        print("⚠️  YOLOv8模型不存在，将在首次使用时自动下载")

print("\n" + "="*70)
print("📋 使用说明")
print("="*70)
print("""
方案A: 使用临时模型（立即可用）
- ✅ 已设置: models/road_damage_yolov8.pt
- ✅ 可在Streamlit中选择"路面缺陷专用模型"
- ⚠️  当前是通用模型，检测效果有限

方案B: 训练专用模型（推荐）
1. 下载RDD2020数据集
2. 准备数据格式（见训练脚本说明）
3. 运行: python quick_train_model.py
4. 训练完成后自动替换模型

方案C: 下载预训练模型
1. 访问: https://universe.roboflow.com/
2. 搜索: "road damage detection yolov8"
3. 下载.pt文件
4. 重命名为: models/road_damage_yolov8.pt
""")

print("\n✅ 准备完成!")
print(f"   模型目录: {models_dir}/")
print(f"   训练脚本: {script_path}")
print("\n🌐 刷新Streamlit页面即可使用!")
