#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Roboflow路面缺陷检测模型进行真实检测
"""
import sys
import io
import cv2
import numpy as np
from pathlib import Path

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_roboflow_detection():
    print("="*60)
    print("路面缺陷检测 - Roboflow专用模型")
    print("="*60)
    print()
    
    # 导入Roboflow SDK
    try:
        from inference_sdk import InferenceHTTPClient
        print("✅ inference_sdk导入成功")
    except ImportError:
        print("❌ 请先安装: pip install inference-sdk")
        return
    
    # 初始化客户端
    print("\n📡 连接Roboflow服务器...")
    CLIENT = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key="oXTHrkxznyByqHg4keH7"
    )
    print("✅ 连接成功")
    
    # 使用测试图片（如果没有真实路面图片，用我们创建的）
    test_images = [
        'samples/crack_test.jpg',
        'samples/pothole_test.jpg',
        'samples/mixed_test.jpg',
    ]
    
    output_dir = Path('roboflow_output')
    output_dir.mkdir(exist_ok=True)
    
    for img_path in test_images:
        if not Path(img_path).exists():
            print(f"⚠️  文件不存在: {img_path}")
            continue
        
        print(f"\n📷 检测图片: {img_path}")
        print("   模型: road-defect-detection-ff7jh/1")
        
        try:
            # 调用Roboflow API
            result = CLIENT.infer(img_path, model_id="road-defect-detection-ff7jh/1")
            
            # 解析结果
            if 'predictions' in result:
                predictions = result['predictions']
                print(f"   检测到: {len(predictions)} 个缺陷")
                
                if len(predictions) > 0:
                    print("\n   检测详情:")
                    for i, pred in enumerate(predictions, 1):
                        class_name = pred.get('class', 'unknown')
                        confidence = pred.get('confidence', 0)
                        x = pred.get('x', 0)
                        y = pred.get('y', 0)
                        width = pred.get('width', 0)
                        height = pred.get('height', 0)
                        
                        print(f"     {i}. {class_name}")
                        print(f"        置信度: {confidence:.2f}")
                        print(f"        位置: (x={x:.0f}, y={y:.0f}, w={width:.0f}, h={height:.0f})")
                    
                    # 可视化结果
                    visualize_predictions(img_path, predictions, output_dir)
                else:
                    print("   (未检测到缺陷)")
            else:
                print(f"   响应格式: {result.keys()}")
                
        except Exception as e:
            print(f"   ❌ 检测失败: {e}")
    
    print("\n" + "="*60)
    print("✅ 检测完成!")
    print(f"💾 结果保存在: {output_dir}/")
    print("="*60)

def visualize_predictions(image_path, predictions, output_dir):
    """可视化检测结果"""
    # 读取图片
    img = cv2.imread(str(image_path))
    if img is None:
        return
    
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
        
        # 绘制边界框
        color = (0, 255, 0)  # 绿色
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        
        # 绘制标签
        label = f'{class_name}: {confidence:.2f}'
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(img, (x1, y1 - label_size[1] - 10), 
                     (x1 + label_size[0] + 10, y1), color, -1)
        cv2.putText(img, label, (x1 + 5, y1 - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # 保存结果
    output_path = output_dir / f'result_{Path(image_path).name}'
    cv2.imwrite(str(output_path), img)
    print(f"   💾 可视化结果: {output_path}")

if __name__ == '__main__':
    test_roboflow_detection()
