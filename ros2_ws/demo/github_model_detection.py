#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用GitHub Road-Damage-and-Defect-Recognition-Model
从Gabi-comm仓库下载并运行路面缺陷检测模型
"""
import sys
import io
import cv2
import numpy as np
from pathlib import Path
import urllib.request
import zipfile
import os

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def download_model_from_github():
    """从GitHub仓库下载预训练模型"""
    print("="*70)
    print("路面缺陷检测模型 - GitHub: Gabi-comm/Road-Damage-and-Defect-Recognition-Model")
    print("="*70)
    print()
    
    # 模型目录
    model_dir = Path('models/road_damage_github')
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print("📦 准备下载模型...")
    print(f"   仓库: https://github.com/Gabi-comm/Road-Damage-and-Defect-Recognition-Model")
    
    # GitHub仓库的模型文件URL（需要根据实际仓库内容调整）
    # 通常YOLOv8模型会在releases或者直接在仓库中
    model_urls = {
        'best.pt': 'https://github.com/Gabi-comm/Road-Damage-and-Defect-Recognition-Model/raw/main/best.pt',
        'yolov8_road_damage.pt': 'https://github.com/Gabi-comm/Road-Damage-and-Defect-Recognition-Model/raw/main/runs/detect/train/weights/best.pt',
    }
    
    model_path = None
    
    for filename, url in model_urls.items():
        filepath = model_dir / filename
        
        if filepath.exists():
            print(f"✅ 模型已存在: {filepath}")
            model_path = filepath
            break
        
        print(f"\n📥 尝试下载: {filename}")
        print(f"   URL: {url}")
        
        try:
            urllib.request.urlretrieve(url, filepath)
            print(f"✅ 下载成功: {filepath}")
            model_path = filepath
            break
        except Exception as e:
            print(f"⚠️  下载失败: {e}")
    
    return model_path

def run_detection_with_github_model(model_path, image_path):
    """使用GitHub模型进行检测"""
    if model_path is None or not Path(model_path).exists():
        print("❌ 模型文件不存在")
        return None
    
    print(f"\n🔍 使用模型检测: {model_path}")
    print(f"📷 检测图片: {image_path}")
    
    try:
        from ultralytics import YOLO
        
        # 加载模型
        print("\n📦 加载模型...")
        model = YOLO(str(model_path))
        print("✅ 模型加载成功")
        
        # 检测
        print(f"\n🔍 正在检测...")
        results = model(image_path, conf=0.25)
        
        # 解析结果
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                
                detections.append({
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': confidence,
                    'class_id': class_id,
                    'class_name': class_name
                })
        
        print(f"\n✅ 检测完成!")
        print(f"   检测到: {len(detections)} 个路面缺陷")
        
        if len(detections) > 0:
            print("\n📊 检测详情:")
            # 统计类别
            class_counts = {}
            for det in detections:
                cls = det['class_name']
                class_counts[cls] = class_counts.get(cls, 0) + 1
            
            print("   缺陷类型统计:")
            for cls, count in class_counts.items():
                print(f"     - {cls}: {count}个")
            
            print("\n   详细信息:")
            for i, det in enumerate(detections[:10], 1):
                print(f"     {i}. {det['class_name']}")
                print(f"        置信度: {det['confidence']:.2%}")
                print(f"        位置: {det['bbox']}")
            
            if len(detections) > 10:
                print(f"     ... (还有{len(detections)-10}个)")
        
        return results, detections
        
    except Exception as e:
        print(f"❌ 检测失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def visualize_results(image_path, detections, output_path):
    """可视化检测结果"""
    img = cv2.imread(str(image_path))
    if img is None:
        return
    
    # 定义颜色
    colors = {
        0: (255, 0, 0),     # 蓝色
        1: (0, 255, 0),     # 绿色
        2: (0, 0, 255),     # 红色
        3: (255, 255, 0),   # 青色
        4: (255, 0, 255),   # 品红
    }
    
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        confidence = det['confidence']
        class_name = det['class_name']
        class_id = det['class_id']
        
        # 颜色
        color = colors.get(class_id % 5, (128, 128, 128))
        
        # 边界框
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        
        # 标签
        label = f'{class_name}: {confidence:.2%}'
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(img, (x1, y1 - label_size[1] - 12), 
                     (x1 + label_size[0] + 8, y1), color, -1)
        cv2.putText(img, label, (x1 + 4, y1 - 6), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # 统计信息
    stats = f'Detected: {len(detections)} road defects'
    cv2.putText(img, stats, (20, 50), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
    
    # 保存
    cv2.imwrite(str(output_path), img)
    print(f"\n💾 可视化结果已保存: {output_path}")

def main():
    # 下载模型
    model_path = download_model_from_github()
    
    if model_path is None:
        print("\n⚠️  无法下载模型")
        print("请手动下载:")
        print("1. 访问: https://github.com/Gabi-comm/Road-Damage-and-Defect-Recognition-Model")
        print("2. 下载预训练模型文件 (best.pt 或类似文件)")
        print("3. 放置到: models/road_damage_github/")
        print("4. 重新运行此脚本")
        return
    
    # 测试图片
    test_images = [
        'samples/crack_test.jpg',
        'samples/pothole_test.jpg',
        'samples/mixed_test.jpg',
    ]
    
    # 输出目录
    output_dir = Path('github_model_results')
    output_dir.mkdir(exist_ok=True)
    
    # 测试第一张图片
    for img_path in test_images[:1]:
        if Path(img_path).exists():
            results, detections = run_detection_with_github_model(model_path, img_path)
            
            if detections is not None and len(detections) > 0:
                output_path = output_dir / f'github_{Path(img_path).name}'
                visualize_results(img_path, detections, output_path)
            
            break
    
    print("\n" + "="*70)
    print("✅ GitHub模型检测完成!")
    print(f"📁 结果保存在: {output_dir}/")
    print("="*70)

if __name__ == '__main__':
    main()
