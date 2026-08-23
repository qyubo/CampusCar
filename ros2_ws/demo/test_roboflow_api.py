#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Roboflow API直接调用路面缺陷检测模型
不依赖inference-sdk，使用标准库requests
"""
import sys
import io
import requests
import cv2
import numpy as np
from pathlib import Path
import base64
import json

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Roboflow API配置
API_URL = "https://detect.roboflow.com/road-defect-detection-ff7jh/1"
API_KEY = "oXTHrkxznyByqHg4keH7"

def detect_with_roboflow(image_path):
    """使用Roboflow API检测图片"""
    print(f"\n📷 检测图片: {image_path}")
    
    # 读取图片并编码为base64
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    image_b64 = base64.b64encode(image_data).decode('utf-8')
    
    # 构建请求
    url = f"{API_URL}?api_key={API_KEY}&confidence=40&overlap=30"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    print("   ⏳ 正在调用Roboflow API...")
    
    try:
        # 发送请求
        response = requests.post(url, data=image_b64, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"   ❌ API返回错误: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
        return None

def visualize_predictions(image_path, predictions, output_dir):
    """可视化检测结果"""
    # 读取图片
    img = cv2.imread(str(image_path))
    if img is None:
        return None
    
    img_height, img_width = img.shape[:2]
    
    # 定义颜色映射
    colors = {
        'D00': (255, 0, 0),     # 横向裂缝 - 蓝色
        'D10': (0, 255, 0),     # 纵向裂缝 - 绿色
        'D20': (0, 255, 255),   # 龟裂 - 黄色
        'D40': (0, 0, 255),     # 坑槽 - 红色
        'default': (255, 255, 0)  # 默认 - 青色
    }
    
    # 绘制检测框
    for pred in predictions:
        class_name = pred.get('class', 'unknown')
        confidence = pred.get('confidence', 0)
        x = pred.get('x', 0)
        y = pred.get('y', 0)
        width = pred.get('width', 0)
        height = pred.get('height', 0)
        
        # 转换为左上角和右下角坐标
        x1 = int(x - width / 2)
        y1 = int(y - height / 2)
        x2 = int(x + width / 2)
        y2 = int(y + height / 2)
        
        # 选择颜色
        color = colors.get(class_name, colors['default'])
        
        # 绘制边界框
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        
        # 绘制标签背景
        label = f'{class_name}: {confidence:.2f}'
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(img, (x1, y1 - label_size[1] - 15), 
                     (x1 + label_size[0] + 10, y1), color, -1)
        
        # 绘制标签文字
        cv2.putText(img, label, (x1 + 5, y1 - 8), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # 添加统计信息
    info_text = f'Detected: {len(predictions)} defects'
    cv2.putText(img, info_text, (20, 40), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    
    # 保存结果
    output_path = output_dir / f'roboflow_{Path(image_path).name}'
    cv2.imwrite(str(output_path), img)
    
    return output_path

def main():
    print("="*70)
    print("路面缺陷检测 - Roboflow专用模型 (road-defect-detection-ff7jh/1)")
    print("="*70)
    
    # 测试图片列表
    test_images = [
        'samples/crack_test.jpg',
        'samples/pothole_test.jpg',
        'samples/mixed_test.jpg',
    ]
    
    # 创建输出目录
    output_dir = Path('roboflow_output')
    output_dir.mkdir(exist_ok=True)
    
    total_detections = 0
    successful = 0
    
    for img_path in test_images:
        if not Path(img_path).exists():
            print(f"\n⚠️  文件不存在: {img_path}")
            continue
        
        # 检测
        result = detect_with_roboflow(img_path)
        
        if result and 'predictions' in result:
            predictions = result['predictions']
            num_detections = len(predictions)
            total_detections += num_detections
            successful += 1
            
            print(f"   ✅ 检测到: {num_detections} 个缺陷")
            
            if num_detections > 0:
                print("\n   检测详情:")
                for i, pred in enumerate(predictions, 1):
                    class_name = pred.get('class', 'unknown')
                    confidence = pred.get('confidence', 0)
                    print(f"     {i}. {class_name} - 置信度: {confidence:.2%}")
                
                # 可视化
                output_path = visualize_predictions(img_path, predictions, output_dir)
                if output_path:
                    print(f"   💾 结果已保存: {output_path}")
            else:
                print("   (未检测到缺陷)")
        else:
            print("   ❌ 检测失败")
    
    print("\n" + "="*70)
    print("📊 检测总结:")
    print(f"   - 成功检测: {successful}/{len(test_images)} 张图片")
    print(f"   - 总共发现: {total_detections} 个缺陷")
    print(f"   - 结果保存: {output_dir}/")
    print("="*70)
    print("\n✅ 检测完成!")

if __name__ == '__main__':
    main()
