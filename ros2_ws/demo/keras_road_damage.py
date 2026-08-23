#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用GitHub Keras模型检测路面缺陷
仓库: Gabi-comm/Road-Damage-and-Defect-Recognition-Model
模型框架: Keras/TensorFlow (H5格式)
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

def setup_keras_model():
    """设置Keras模型环境"""
    print("="*70)
    print("Keras路面缺陷检测 - GitHub Model")
    print("="*70)
    print()
    
    try:
        import tensorflow as tf
        from tensorflow import keras
        print(f"✅ TensorFlow版本: {tf.__version__}")
        print(f"✅ Keras版本: {keras.__version__}")
        return True
    except ImportError:
        print("❌ TensorFlow未安装")
        print("📦 安装命令: pip install tensorflow")
        return False

def clone_repository():
    """克隆GitHub仓库"""
    repo_dir = Path('Road-Damage-and-Defect-Recognition-Model')
    
    if repo_dir.exists():
        print(f"✅ 仓库已存在: {repo_dir}")
        return repo_dir
    
    print("\n📥 克隆GitHub仓库...")
    print("   仓库: Gabi-comm/Road-Damage-and-Defect-Recognition-Model")
    
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'clone', 'https://github.com/Gabi-comm/Road-Damage-and-Defect-Recognition-Model.git'],
            capture_output=True,
            text=True,
            cwd='.'
        )
        
        if result.returncode == 0:
            print(f"✅ 克隆成功: {repo_dir}")
            return repo_dir
        else:
            print(f"❌ 克隆失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ 克隆失败: {e}")
        return None

def find_model_file(repo_dir):
    """查找模型文件"""
    if repo_dir is None or not repo_dir.exists():
        return None
    
    print("\n🔍 查找模型文件...")
    
    # 常见的模型文件名
    model_patterns = [
        '*.h5',
        '*.hdf5',
        '*.keras',
        '*model*.h5',
        'best*.h5',
    ]
    
    for pattern in model_patterns:
        models = list(repo_dir.rglob(pattern))
        if models:
            model_path = models[0]
            print(f"✅ 找到模型: {model_path}")
            return model_path
    
    print("⚠️  未找到预训练模型文件")
    print("   可能需要先运行Jupyter Notebook训练模型")
    return None

def load_keras_model(model_path):
    """加载Keras模型"""
    if model_path is None or not Path(model_path).exists():
        return None
    
    print(f"\n📦 加载Keras模型: {model_path}")
    
    try:
        from tensorflow import keras
        model = keras.models.load_model(str(model_path))
        print("✅ 模型加载成功")
        
        # 打印模型信息
        print(f"\n📊 模型信息:")
        print(f"   输入形状: {model.input_shape}")
        print(f"   输出形状: {model.output_shape}")
        
        return model
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return None

def preprocess_image(image_path, target_size=(224, 224)):
    """预处理图片"""
    img = cv2.imread(str(image_path))
    if img is None:
        return None
    
    # 转换颜色空间
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 调整大小
    img = cv2.resize(img, target_size)
    
    # 归一化
    img = img.astype(np.float32) / 255.0
    
    # 添加batch维度
    img = np.expand_dims(img, axis=0)
    
    return img

def predict_with_keras_model(model, image_path):
    """使用Keras模型进行预测"""
    print(f"\n📷 处理图片: {image_path}")
    
    # 获取输入尺寸
    input_shape = model.input_shape[1:3]  # (height, width)
    
    # 预处理
    img = preprocess_image(image_path, target_size=input_shape)
    if img is None:
        print(f"❌ 无法读取图片")
        return None
    
    # 预测
    print("🔍 正在预测...")
    predictions = model.predict(img, verbose=0)
    
    return predictions

def interpret_predictions(predictions, class_names=None):
    """解释预测结果"""
    if predictions is None:
        return
    
    print(f"\n📊 预测结果:")
    print(f"   输出形状: {predictions.shape}")
    
    # 如果是分类任务
    if len(predictions.shape) == 2:
        if class_names is None:
            # RDD2020常见类别
            class_names = ['D00', 'D10', 'D20', 'D40', 'D43', 'D44']
        
        # 获取预测类别
        pred_class = np.argmax(predictions[0])
        confidence = predictions[0][pred_class]
        
        print(f"\n   预测类别: {class_names[pred_class] if pred_class < len(class_names) else f'Class {pred_class}'}")
        print(f"   置信度: {confidence:.2%}")
        
        # 显示所有类别的概率
        print(f"\n   各类别概率:")
        for i, prob in enumerate(predictions[0]):
            class_name = class_names[i] if i < len(class_names) else f'Class {i}'
            print(f"     {class_name}: {prob:.2%}")
    else:
        print(f"   原始输出: {predictions}")

def run_streamlit_app(repo_dir):
    """运行Streamlit应用（如果存在）"""
    if repo_dir is None:
        return
    
    app_file = repo_dir / 'app.py'
    if not app_file.exists():
        print("\n⚠️  未找到app.py，无法运行Streamlit应用")
        return
    
    print("\n🌐 发现Streamlit应用!")
    print("   运行命令:")
    print(f"   cd {repo_dir}")
    print(f"   streamlit run app.py")

def main():
    # 检查TensorFlow
    if not setup_keras_model():
        print("\n请先安装TensorFlow:")
        print("pip install tensorflow")
        return
    
    # 克隆仓库
    repo_dir = clone_repository()
    
    if repo_dir is None:
        print("\n⚠️  无法克隆仓库")
        print("请手动克隆:")
        print("git clone https://github.com/Gabi-comm/Road-Damage-and-Defect-Recognition-Model.git")
        return
    
    # 查找模型
    model_path = find_model_file(repo_dir)
    
    if model_path is None:
        print("\n⚠️  未找到预训练模型")
        print("\n选项:")
        print("1. 运行仓库中的Jupyter Notebook训练模型")
        print("2. 从作者处获取预训练的.h5文件")
        print("3. 使用Streamlit应用（如果有）")
        
        # 检查Streamlit应用
        run_streamlit_app(repo_dir)
        return
    
    # 加载模型
    model = load_keras_model(model_path)
    
    if model is None:
        return
    
    # 测试图片
    test_images = [
        'samples/crack_test.jpg',
        'samples/pothole_test.jpg',
        'samples/mixed_test.jpg',
    ]
    
    # 测试第一张图片
    for img_path in test_images[:1]:
        if Path(img_path).exists():
            predictions = predict_with_keras_model(model, img_path)
            if predictions is not None:
                interpret_predictions(predictions)
            break
    
    print("\n" + "="*70)
    print("✅ Keras模型测试完成!")
    print("="*70)

if __name__ == '__main__':
    main()
