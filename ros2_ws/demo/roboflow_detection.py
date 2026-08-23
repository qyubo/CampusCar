#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roboflow路面缺陷检测 - 使用官方SDK
模型: road-defect-detection-ff7jh/1
"""
import sys
import io
import cv2
import numpy as np
from pathlib import Path
import json

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def run_roboflow_detection(image_path, api_key="oXTHrkxznyByqHg4keH7"):
    """
    使用Roboflow模型检测路面缺陷
    
    Args:
        image_path: 图片路径
        api_key: Roboflow API密钥
    """
    print("="*70)
    print("Roboflow路面缺陷检测 - road-defect-detection-ff7jh/1")
    print("="*70)
    print()
    
    try:
        from roboflow import Roboflow
        print("✅ Roboflow SDK导入成功")
    except ImportError:
        print("❌ 请先安装: pip install roboflow")
        return None
    
    print(f"\n📷 加载图片: {image_path}")
    
    # 检查图片是否存在
    if not Path(image_path).exists():
        print(f"❌ 图片不存在: {image_path}")
        return None
    
    try:
        # 初始化Roboflow
        print("\n📡 初始化Roboflow客户端...")
        rf = Roboflow(api_key=api_key)
        
        # 加载项目和模型
        print("📦 加载模型: road-defect-detection-ff7jh/1...")
        project = rf.workspace().project("road-defect-detection-ff7jh")
        model = project.version(1).model
        
        print("✅ 模型加载成功")
        
        # 运行推理
        print(f"\n🔍 正在检测: {image_path}")
        print("   (这可能需要几秒钟...)")
        
        result = model.predict(image_path, confidence=40, overlap=30).json()
        
        # 解析结果
        predictions = result.get('predictions', [])
        
        print(f"\n✅ 检测完成!")
        print(f"   检测到: {len(predictions)} 个路面缺陷")
        
        if len(predictions) > 0:
            print("\n📊 检测详情:")
            print("   " + "-"*60)
            
            # 统计各类缺陷
            defect_types = {}
            for pred in predictions:
                class_name = pred.get('class', 'unknown')
                defect_types[class_name] = defect_types.get(class_name, 0) + 1
            
            print(f"   缺陷类型统计:")
            for dtype, count in defect_types.items():
                print(f"     - {dtype}: {count}个")
            
            print("\n   详细信息:")
            for i, pred in enumerate(predictions[:10], 1):  # 只显示前10个
                class_name = pred.get('class', 'unknown')
                confidence = pred.get('confidence', 0)
                x = pred.get('x', 0)
                y = pred.get('y', 0)
                width = pred.get('width', 0)
                height = pred.get('height', 0)
                
                print(f"     {i}. {class_name}")
                print(f"        置信度: {confidence:.2%}")
                print(f"        位置: (x={x:.0f}, y={y:.0f})")
                print(f"        尺寸: {width:.0f}x{height:.0f}px")
            
            if len(predictions) > 10:
                print(f"     ... (还有{len(predictions)-10}个)")
        else:
            print("   ⚠️  未检测到路面缺陷")
        
        return result
        
    except Exception as e:
        print(f"\n❌ 检测失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def visualize_roboflow_results(image_path, result, output_path):
    """可视化Roboflow检测结果"""
    if result is None:
        return
    
    # 读取图片
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"❌ 无法读取图片: {image_path}")
        return
    
    predictions = result.get('predictions', [])
    
    if len(predictions) == 0:
        print("⚠️  没有检测结果可视化")
        return
    
    # 定义缺陷类型颜色
    colors = {
        'D00': (255, 0, 0),      # 横向裂缝 - 蓝色
        'D10': (0, 255, 0),      # 纵向裂缝 - 绿色
        'D20': (0, 255, 255),    # 龟裂 - 黄色
        'D40': (0, 0, 255),      # 坑槽 - 红色
        'D43': (255, 0, 255),    # 交叉损坏 - 品红
        'D44': (255, 255, 0),    # 沉降 - 青色
        'default': (128, 128, 128)  # 默认 - 灰色
    }
    
    # 绘制所有检测框
    for pred in predictions:
        class_name = pred.get('class', 'unknown')
        confidence = pred.get('confidence', 0)
        x = pred.get('x', 0)
        y = pred.get('y', 0)
        width = pred.get('width', 0)
        height = pred.get('height', 0)
        
        # 转换坐标
        x1 = int(x - width / 2)
        y1 = int(y - height / 2)
        x2 = int(x + width / 2)
        y2 = int(y + height / 2)
        
        # 选择颜色
        color = colors.get(class_name, colors['default'])
        
        # 绘制边界框
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        
        # 绘制标签
        label = f'{class_name}: {confidence:.1%}'
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        
        # 标签背景
        cv2.rectangle(img, (x1, y1 - label_size[1] - 12), 
                     (x1 + label_size[0] + 8, y1), color, -1)
        
        # 标签文字
        cv2.putText(img, label, (x1 + 4, y1 - 6), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 添加统计信息
    stats_text = f'Detected: {len(predictions)} road defects'
    cv2.putText(img, stats_text, (20, 50), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
    
    # 保存结果
    cv2.imwrite(str(output_path), img)
    print(f"\n💾 可视化结果已保存: {output_path}")

def main():
    # 测试图片
    test_images = [
        'samples/crack_test.jpg',
        'samples/pothole_test.jpg',
        'samples/mixed_test.jpg',
    ]
    
    # 输出目录
    output_dir = Path('roboflow_results')
    output_dir.mkdir(exist_ok=True)
    
    # API密钥（从环境变量读取，或使用默认值）
    import os
    api_key = os.environ.get('ROBOFLOW_API_KEY', 'oXTHrkxznyByqHg4keH7')
    
    # 测试第一张图片
    for img_path in test_images[:1]:  # 只测试第一张
        if Path(img_path).exists():
            result = run_roboflow_detection(img_path, api_key)
            
            if result:
                # 可视化
                output_path = output_dir / f'roboflow_{Path(img_path).name}'
                visualize_roboflow_results(img_path, result, output_path)
                
                # 保存JSON结果
                json_path = output_dir / f'result_{Path(img_path).stem}.json'
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"💾 JSON结果已保存: {json_path}")
            
            break  # 只测试第一张图片
    
    print("\n" + "="*70)
    print("✅ Roboflow检测完成!")
    print(f"📁 结果保存在: {output_dir}/")
    print("="*70)

if __name__ == '__main__':
    main()
