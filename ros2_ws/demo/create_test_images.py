#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成测试图片 - 模拟路面缺陷用于Demo测试
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

def create_test_images():
    """创建测试用的路面图片"""
    output_dir = Path('samples')
    output_dir.mkdir(exist_ok=True)
    
    # 创建1: 路面裂缝图片
    img1 = np.ones((1080, 1920, 3), dtype=np.uint8) * 100  # 灰色路面
    
    # 绘制裂缝（黑色线条）
    cv2.line(img1, (500, 300), (800, 700), (30, 30, 30), 5)
    cv2.line(img1, (800, 700), (1200, 900), (30, 30, 30), 5)
    cv2.line(img1, (1200, 300), (1400, 600), (30, 30, 30), 4)
    
    # 添加噪声增加真实感
    noise = np.random.normal(0, 15, img1.shape).astype(np.int16)
    img1 = np.clip(img1.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    cv2.imwrite(str(output_dir / 'crack_test.jpg'), img1)
    print(f"✅ 创建测试图片1: {output_dir / 'crack_test.jpg'}")
    
    # 创建2: 坑槽图片
    img2 = np.ones((1080, 1920, 3), dtype=np.uint8) * 110
    
    # 绘制坑槽（深色圆形区域）
    cv2.circle(img2, (800, 500), 80, (40, 40, 40), -1)
    cv2.circle(img2, (800, 500), 85, (50, 50, 50), 3)
    
    cv2.circle(img2, (1200, 700), 60, (45, 45, 45), -1)
    cv2.circle(img2, (1200, 700), 65, (55, 55, 55), 3)
    
    # 添加噪声
    noise = np.random.normal(0, 15, img2.shape).astype(np.int16)
    img2 = np.clip(img2.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    cv2.imwrite(str(output_dir / 'pothole_test.jpg'), img2)
    print(f"✅ 创建测试图片2: {output_dir / 'pothole_test.jpg'}")
    
    # 创建3: 复杂路面
    img3 = np.ones((1080, 1920, 3), dtype=np.uint8) * 105
    
    # 混合多种缺陷
    cv2.line(img3, (400, 400), (600, 800), (35, 35, 35), 4)
    cv2.circle(img3, (1000, 600), 70, (40, 40, 40), -1)
    cv2.line(img3, (1300, 200), (1500, 900), (30, 30, 30), 5)
    
    # 添加路面纹理
    for i in range(0, 1920, 100):
        cv2.line(img3, (i, 0), (i, 1080), (95, 95, 95), 1)
    for j in range(0, 1080, 100):
        cv2.line(img3, (0, j), (1920, j), (95, 95, 95), 1)
    
    noise = np.random.normal(0, 20, img3.shape).astype(np.int16)
    img3 = np.clip(img3.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    cv2.imwrite(str(output_dir / 'mixed_test.jpg'), img3)
    print(f"✅ 创建测试图片3: {output_dir / 'mixed_test.jpg'}")
    
    print("\n测试图片已创建在 samples/ 目录")
    return [
        output_dir / 'crack_test.jpg',
        output_dir / 'pothole_test.jpg',
        output_dir / 'mixed_test.jpg'
    ]

if __name__ == '__main__':
    create_test_images()
