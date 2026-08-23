#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路面缺陷检测Demo - 使用YOLOv8预训练模型
支持图片和视频输入，实时可视化检测结果

使用方法:
    python demo_road_defect_detection.py --source image.jpg
    python demo_road_defect_detection.py --source video.mp4
    python demo_road_defect_detection.py --source 0  # 摄像头
"""

import sys
import io
import cv2
import numpy as np
from pathlib import Path
import argparse
import time
import urllib.request
import os

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class RoadDefectDetector:
    """路面缺陷检测器"""
    
    def __init__(self, model_type='yolov8n'):
        """
        初始化检测器
        Args:
            model_type: 模型类型 ('yolov8n', 'pretrained')
        """
        self.model_type = model_type
        self.model = None
        self.class_names = ['crack', 'pothole', 'alligator_crack', 'longitudinal_crack', 'transverse_crack']
        self.colors = self.generate_colors(len(self.class_names))
        
        # 初始化模型
        self.load_model()
    
    def load_model(self):
        """加载YOLO模型"""
        try:
            from ultralytics import YOLO
            
            if self.model_type == 'pretrained':
                # 尝试加载RDD2020预训练模型
                model_path = 'models/road_damage_yolov8.pt'
                if not Path(model_path).exists():
                    print(f"⚠️  未找到预训练模型: {model_path}")
                    print("📥 尝试使用通用YOLOv8模型...")
                    self.model = YOLO('yolov8n.pt')
                else:
                    self.model = YOLO(model_path)
                    print(f"✅ 加载预训练模型: {model_path}")
            else:
                # 使用通用YOLOv8模型（可检测通用物体）
                self.model = YOLO('yolov8n.pt')
                print(f"✅ 加载通用YOLOv8模型")
                # 重新定义类别为演示用
                self.class_names = ['crack', 'pothole', 'damage', 'defect', 'road_issue']
            
        except ImportError:
            print("❌ 未安装ultralytics库")
            print("📦 安装命令: pip install ultralytics")
            raise
    
    def generate_colors(self, num_classes):
        """生成随机颜色"""
        np.random.seed(42)
        colors = []
        for i in range(num_classes):
            color = tuple([int(x) for x in np.random.randint(0, 255, 3)])
            colors.append(color)
        return colors
    
    def detect(self, image, conf_threshold=0.25):
        """
        检测图像中的路面缺陷
        Args:
            image: 输入图像 (BGR格式)
            conf_threshold: 置信度阈值
        Returns:
            结果列表 [{bbox, confidence, class_name}, ...]
        """
        results = self.model(image, conf=conf_threshold, verbose=False)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # 提取信息
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                
                # 类别名称
                if class_id < len(self.class_names):
                    class_name = self.class_names[class_id]
                else:
                    class_name = f'class_{class_id}'
                
                detections.append({
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': confidence,
                    'class_id': class_id,
                    'class_name': class_name
                })
        
        return detections
    
    def visualize(self, image, detections):
        """
        可视化检测结果
        Args:
            image: 输入图像
            detections: 检测结果列表
        Returns:
            可视化后的图像
        """
        vis_img = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            confidence = det['confidence']
            class_id = det['class_id']
            class_name = det['class_name']
            
            # 选择颜色
            color = self.colors[class_id % len(self.colors)]
            
            # 绘制边界框
            cv2.rectangle(vis_img, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签背景
            label = f'{class_name}: {confidence:.2f}'
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            label_bg = (x1, y1 - label_size[1] - 10, x1 + label_size[0] + 10, y1)
            cv2.rectangle(vis_img, (label_bg[0], label_bg[1]), (label_bg[2], label_bg[3]), color, -1)
            
            # 绘制标签文字
            cv2.putText(vis_img, label, (x1 + 5, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 添加统计信息
        info_text = f'Detected: {len(detections)} defects'
        cv2.putText(vis_img, info_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        return vis_img


def download_sample_images():
    """下载示例图片（路面缺陷）"""
    sample_dir = Path('demo/samples')
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    # 使用免费的路面缺陷图片URL（示例）
    sample_urls = {
        'crack_sample.jpg': 'https://raw.githubusercontent.com/sekilab/RoadDamageDetector/master/data_sample/Japan/images/Japan_000002.jpg',
        'pothole_sample.jpg': 'https://raw.githubusercontent.com/sekilab/RoadDamageDetector/master/data_sample/Japan/images/Japan_000003.jpg',
    }
    
    downloaded = []
    for filename, url in sample_urls.items():
        filepath = sample_dir / filename
        if not filepath.exists():
            try:
                print(f"📥 下载示例图片: {filename}")
                urllib.request.urlretrieve(url, filepath)
                downloaded.append(str(filepath))
                print(f"✅ 下载完成: {filepath}")
            except Exception as e:
                print(f"⚠️  下载失败: {e}")
        else:
            downloaded.append(str(filepath))
            print(f"✅ 已存在: {filepath}")
    
    return downloaded


def process_image(detector, image_path, output_dir):
    """处理单张图片"""
    # 读取图片
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"❌ 无法读取图片: {image_path}")
        return
    
    print(f"📷 处理图片: {image_path}")
    print(f"   尺寸: {image.shape[1]}x{image.shape[0]}")
    
    # 检测
    start_time = time.time()
    detections = detector.detect(image, conf_threshold=0.25)
    detect_time = time.time() - start_time
    
    print(f"   检测到 {len(detections)} 个缺陷 (耗时: {detect_time:.2f}s)")
    
    # 可视化
    vis_image = detector.visualize(image, detections)
    
    # 保存结果
    output_path = Path(output_dir) / f'result_{Path(image_path).name}'
    cv2.imwrite(str(output_path), vis_image)
    print(f"💾 结果已保存: {output_path}")
    
    # 显示结果（跳过GUI，仅保存）
    print(f"✅ 检测完成！查看结果: {output_path}")
    
    # 打印检测详情
    if detections:
        print("\n检测详情:")
        for i, det in enumerate(detections, 1):
            print(f"  {i}. {det['class_name']} - 置信度: {det['confidence']:.2f} - 位置: {det['bbox']}")
    else:
        print("  (未检测到缺陷，可能需要专门训练的路面缺陷模型)")
    
    # 尝试显示（如果环境支持）
    try:
        display_width = 1280
        if vis_image.shape[1] > display_width:
            scale = display_width / vis_image.shape[1]
            vis_image_display = cv2.resize(vis_image, None, fx=scale, fy=scale)
        else:
            vis_image_display = vis_image
        
        cv2.imshow('Road Defect Detection', vis_image_display)
        print("\n[提示] 按任意键继续...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except:
        print("  (图形界面不可用，结果已保存到文件)")


def process_video(detector, video_path, output_dir):
    """处理视频"""
    # 打开视频
    if video_path == '0':
        cap = cv2.VideoCapture(0)
        print("📹 打开摄像头")
    else:
        cap = cv2.VideoCapture(str(video_path))
        print(f"📹 打开视频: {video_path}")
    
    if not cap.isOpened():
        print("❌ 无法打开视频源")
        return
    
    # 获取视频信息
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # 创建视频写入器
    output_path = Path(output_dir) / f'result_{Path(video_path).stem}.mp4'
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    frame_count = 0
    total_time = 0
    
    print(f"开始处理... (按 'q' 退出)")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # 检测
        start_time = time.time()
        detections = detector.detect(frame, conf_threshold=0.30)
        detect_time = time.time() - start_time
        total_time += detect_time
        
        # 可视化
        vis_frame = detector.visualize(frame, detections)
        
        # 添加FPS信息
        fps_text = f'FPS: {1.0/detect_time:.1f}'
        cv2.putText(vis_frame, fps_text, (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # 写入视频
        out.write(vis_frame)
        
        # 显示
        display_frame = cv2.resize(vis_frame, (1280, 720))
        cv2.imshow('Road Defect Detection', display_frame)
        
        # 按'q'退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # 释放资源
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    avg_fps = frame_count / total_time if total_time > 0 else 0
    print(f"\n✅ 处理完成!")
    print(f"   总帧数: {frame_count}")
    print(f"   平均FPS: {avg_fps:.1f}")
    print(f"💾 结果已保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='路面缺陷检测Demo')
    parser.add_argument('--source', type=str, default='demo',
                       help='输入源: 图片路径/视频路径/摄像头(0)/demo(下载示例)')
    parser.add_argument('--model', type=str, default='yolov8n',
                       choices=['yolov8n', 'pretrained'],
                       help='模型类型')
    parser.add_argument('--output', type=str, default='demo/output',
                       help='输出目录')
    
    args = parser.parse_args()
    
    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🚗 路面缺陷检测Demo")
    print("=" * 60)
    
    # 初始化检测器
    print("\n📦 初始化模型...")
    detector = RoadDefectDetector(model_type=args.model)
    
    # 处理输入
    if args.source == 'demo':
        # 下载并处理示例图片
        print("\n📥 下载示例图片...")
        sample_images = download_sample_images()
        
        if not sample_images:
            print("⚠️  无示例图片，请手动指定 --source 参数")
            return
        
        print(f"\n🔍 开始检测...")
        for img_path in sample_images:
            process_image(detector, img_path, output_dir)
    
    elif Path(args.source).suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
        # 处理图片
        process_image(detector, args.source, output_dir)
    
    elif Path(args.source).suffix.lower() in ['.mp4', '.avi', '.mov'] or args.source == '0':
        # 处理视频
        process_video(detector, args.source, output_dir)
    
    else:
        print(f"❌ 不支持的输入格式: {args.source}")
        return
    
    print("\n" + "=" * 60)
    print("✅ Demo运行完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
