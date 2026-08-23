#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整Demo演示 - 使用在线图片展示检测效果
"""
import sys
import io

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from ultralytics import YOLO
import cv2
from pathlib import Path

def run_demo():
    print("="*60)
    print("🚗 路面缺陷检测完整Demo")
    print("="*60)
    print()
    
    # 加载模型
    print("📦 加载YOLOv8模型...")
    model = YOLO('yolov8n.pt')
    print("✅ 模型加载成功\n")
    
    # 使用ultralytics内置的示例图片
    print("📷 下载并检测在线示例图片...")
    print("   图片来源: Ultralytics官方示例")
    
    # 运行检测（会自动下载示例图片）
    results = model('https://ultralytics.com/images/bus.jpg', conf=0.25)
    
    print("\n🔍 检测结果:")
    print("="*60)
    
    # 输出检测详情
    for i, r in enumerate(results):
        print(f"\n图片 {i+1}:")
        print(f"  尺寸: {r.orig_shape}")
        print(f"  检测到: {len(r.boxes)} 个物体")
        
        if len(r.boxes) > 0:
            print("\n  详细检测:")
            for j, box in enumerate(r.boxes):
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                cls_name = model.names[cls_id]
                xyxy = box.xyxy[0].tolist()
                
                print(f"    {j+1}. {cls_name}")
                print(f"       置信度: {conf:.2f}")
                print(f"       边界框: [{xyxy[0]:.0f}, {xyxy[1]:.0f}, {xyxy[2]:.0f}, {xyxy[3]:.0f}]")
        
        # 保存结果
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / 'demo_result.jpg'
        
        # 获取标注后的图片
        annotated = r.plot()
        cv2.imwrite(str(output_path), annotated)
        
        print(f"\n💾 结果已保存: {output_path}")
    
    print("\n" + "="*60)
    print("✅ Demo运行完成!")
    print("="*60)
    print()
    print("💡 说明:")
    print("  - 当前使用通用YOLOv8模型（80类COCO物体）")
    print("  - 若要检测路面缺陷，需要:")
    print("    1. 使用RDD2020训练的专用模型")
    print("    2. 或提供真实路面缺陷图片")
    print()
    print("📖 完整文档: demo/README.md")
    print()

if __name__ == '__main__':
    run_demo()
