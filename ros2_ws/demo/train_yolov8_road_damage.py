#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练YOLOv8路面缺陷检测模型
使用N-RDD2024数据集
"""
import sys
import io

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from ultralytics import YOLO
from pathlib import Path
import shutil

print("="*70)
print("开始训练YOLOv8路面缺陷检测模型")
print("="*70)
print()

# 检查数据集
data_yaml = Path('models/n_rdd2024.yaml')
dataset_path = Path('datasets/n_rdd2024')

if not dataset_path.exists():
    print("❌ 数据集不存在，请先运行: python prepare_dataset.py")
    sys.exit(1)

print("✅ 数据集已找到")

# 统计数据
train_imgs = len(list((dataset_path / 'images' / 'train').glob('*.jpg')))
val_imgs = len(list((dataset_path / 'images' / 'val').glob('*.jpg')))

print(f"📊 数据集规模:")
print(f"   训练集: {train_imgs} 张")
print(f"   验证集: {val_imgs} 张")

if train_imgs == 0:
    print("\n❌ 训练集为空")
    sys.exit(1)

# 加载预训练模型
print("\n📦 加载预训练模型...")
model = YOLO('yolov8n.pt')
print("✅ 模型加载完成")

# 训练参数
print("\n🚀 开始训练...")
print("训练参数:")
print("   Epochs: 20 (快速训练)")
print("   Batch: 8")
print("   Image Size: 640")
print("   Device: CPU")
print()

try:
    results = model.train(
        data=str(data_yaml),
        epochs=20,              # 快速训练20轮
        imgsz=640,
        batch=8,
        device='cpu',           # CPU训练
        project='road_damage_training',
        name='yolov8n_nrdd',
        patience=10,
        save=True,
        save_period=5,
        verbose=True,
        
        # 优化
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
    
    print("\n✅ 训练完成!")
    
    # 复制最佳模型
    best_model = Path('road_damage_training/yolov8n_nrdd/weights/best.pt')
    target_model = Path('models/road_damage_yolov8.pt')
    
    if best_model.exists():
        shutil.copy(best_model, target_model)
        print(f"✅ 最佳模型已保存: {target_model}")
        print("\n🌐 现在可以在Streamlit中使用'路面缺陷专用模型'!")
    
    # 验证
    print("\n📊 模型验证...")
    metrics = model.val()
    print(f"mAP50: {metrics.box.map50:.3f}")
    print(f"mAP50-95: {metrics.box.map:.3f}")
    
except KeyboardInterrupt:
    print("\n⚠️  训练被中断")
except Exception as e:
    print(f"\n❌ 训练出错: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("训练程序结束")
print("="*70)
