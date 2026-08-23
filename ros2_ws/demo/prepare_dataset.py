#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
准备N-RDD2024数据集并开始训练YOLOv8路面缺陷检测模型
"""
import sys
import io
from pathlib import Path
import shutil

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("="*70)
print("N-RDD2024数据集准备与训练")
print("="*70)
print()

# 数据集源路径
source_data = Path(r'C:\Users\xzx15\Desktop\CyberLuban\新建文件夹')
print(f"数据集源路径: {source_data}")

# 检查源路径
if not source_data.exists():
    print(f"❌ 数据集路径不存在: {source_data}")
    sys.exit(1)

print("✅ 数据集路径存在")

# 列出数据集内容
print("\n📂 数据集内容:")
try:
    items = list(source_data.iterdir())
    for item in items[:10]:  # 只显示前10个
        print(f"   - {item.name}")
    if len(items) > 10:
        print(f"   ... (还有{len(items)-10}个文件/文件夹)")
except Exception as e:
    print(f"❌ 无法列出目录: {e}")
    sys.exit(1)

# 目标路径
target_data = Path('datasets/n_rdd2024')
target_data.mkdir(parents=True, exist_ok=True)
print(f"\n目标路径: {target_data}")

# 检查数据集结构
print("\n🔍 分析数据集结构...")

# 查找图片和标注文件
image_files = list(source_data.glob('**/*.jpg')) + list(source_data.glob('**/*.png'))
label_files = list(source_data.glob('**/*.txt'))

print(f"   找到图片: {len(image_files)} 个")
print(f"   找到标注: {len(label_files)} 个")

if len(image_files) == 0:
    print("\n❌ 未找到图片文件")
    print("请确保数据集已正确解压")
    sys.exit(1)

# 创建YOLO格式数据集结构
print("\n📋 创建YOLO数据集结构...")

# 计算训练/验证划分（80/20）
num_train = int(len(image_files) * 0.8)
train_images = image_files[:num_train]
val_images = image_files[num_train:]

print(f"   训练集: {len(train_images)} 张")
print(f"   验证集: {len(val_images)} 张")

# 创建目录
(target_data / 'images' / 'train').mkdir(parents=True, exist_ok=True)
(target_data / 'images' / 'val').mkdir(parents=True, exist_ok=True)
(target_data / 'labels' / 'train').mkdir(parents=True, exist_ok=True)
(target_data / 'labels' / 'val').mkdir(parents=True, exist_ok=True)

print("\n📦 复制数据集文件...")

# 复制训练集
print("   复制训练集...")
for i, img_path in enumerate(train_images[:100], 1):  # 限制100张用于快速训练
    # 复制图片
    dst_img = target_data / 'images' / 'train' / img_path.name
    if not dst_img.exists():
        shutil.copy2(img_path, dst_img)
    
    # 查找对应的标注文件
    label_path = img_path.with_suffix('.txt')
    if label_path.exists():
        dst_label = target_data / 'labels' / 'train' / label_path.name
        if not dst_label.exists():
            shutil.copy2(label_path, dst_label)
    
    if i % 20 == 0:
        print(f"      已复制 {i} 张...")

# 复制验证集
print("   复制验证集...")
for i, img_path in enumerate(val_images[:20], 1):  # 限制20张
    # 复制图片
    dst_img = target_data / 'images' / 'val' / img_path.name
    if not dst_img.exists():
        shutil.copy2(img_path, dst_img)
    
    # 查找对应的标注文件
    label_path = img_path.with_suffix('.txt')
    if label_path.exists():
        dst_label = target_data / 'labels' / 'val' / label_path.name
        if not dst_label.exists():
            shutil.copy2(label_path, dst_label)

print("✅ 数据集准备完成")

# 统计
train_imgs = len(list((target_data / 'images' / 'train').glob('*.jpg')))
val_imgs = len(list((target_data / 'images' / 'val').glob('*.jpg')))
print(f"\n📊 最终数据集:")
print(f"   训练图片: {train_imgs}")
print(f"   验证图片: {val_imgs}")

print("\n" + "="*70)
print("✅ 数据集准备完成，可以开始训练！")
print("="*70)
print("\n运行训练命令:")
print("python train_yolov8_road_damage.py")
