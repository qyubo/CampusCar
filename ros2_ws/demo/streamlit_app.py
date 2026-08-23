#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新Streamlit应用，添加路面缺陷专用模型支持
支持多模型选择
"""
import streamlit as st
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import tempfile

# 页面配置
st.set_page_config(
    page_title="路面缺陷检测系统",
    page_icon="🚗",
    layout="wide"
)

# 标题
st.title("🚗 路面缺陷检测系统")
st.markdown("**基于YOLOv8的实时路面缺陷检测**")

# 侧边栏
st.sidebar.header("⚙️ 模型设置")

# 模型选择
model_options = {
    "YOLOv8n (通用模型)": "yolov8n.pt",
    "路面缺陷专用模型 (训练中)": "models/road_damage_yolov8.pt",
    "RDD2020预训练模型": "models/rdd2020_best.pt"
}

selected_model_name = st.sidebar.selectbox(
    "选择检测模型",
    list(model_options.keys())
)

model_path = model_options[selected_model_name]

# 检查模型是否存在
model_exists = Path(model_path).exists()
if not model_exists and "通用" not in selected_model_name:
    st.sidebar.warning(f"⚠️ 模型文件不存在: {model_path}")
    st.sidebar.info("请下载或训练模型后放置到指定路径")

confidence_threshold = st.sidebar.slider("置信度阈值", 0.0, 1.0, 0.25, 0.05)

# 路面缺陷类别说明
st.sidebar.markdown("---")
st.sidebar.header("📋 缺陷类别")
defect_types = {
    'D00': '横向裂缝',
    'D10': '纵向裂缝',
    'D20': '龟裂',
    'D40': '坑槽',
    'D43': '交叉口损坏',
    'D44': '沉降'
}

with st.sidebar.expander("查看类别说明"):
    for code, name in defect_types.items():
        st.write(f"**{code}**: {name}")

@st.cache_resource
def load_yolo_model(model_path):
    """加载YOLO模型"""
    try:
        from ultralytics import YOLO
        
        if not Path(model_path).exists():
            if "yolov8n.pt" in model_path:
                # 通用模型，自动下载
                model = YOLO('yolov8n.pt')
                return model, True
            else:
                return None, False
        
        model = YOLO(model_path)
        return model, True
    except Exception as e:
        st.error(f"模型加载失败: {e}")
        return None, False

def classify_image(image, model, conf_threshold=0.25):
    """检测图像中的路面缺陷"""
    if model is None:
        return None, []
    
    # 转换PIL到numpy
    img_array = np.array(image)
    
    # YOLOv8检测
    results = model(img_array, conf=conf_threshold, verbose=False)
    
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
    
    # 绘制结果
    annotated = results[0].plot()
    annotated = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
    
    return annotated, detections

# 主界面
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("📤 上传图片")
    
    # 示例图片
    use_sample = st.checkbox("使用示例图片")
    
    if use_sample:
        sample_images = list(Path('samples').glob('*.jpg')) if Path('samples').exists() else []
        if sample_images:
            selected_sample = st.selectbox("选择示例", [img.name for img in sample_images])
            uploaded_file = selected_sample
            image = Image.open(Path('samples') / selected_sample)
        else:
            st.warning("未找到示例图片")
            uploaded_file = None
    else:
        uploaded_file = st.file_uploader(
            "选择路面图片",
            type=['jpg', 'jpeg', 'png'],
            help="支持JPG、JPEG、PNG格式"
        )
    
    if uploaded_file is not None and not use_sample:
        # 显示原图
        image = Image.open(uploaded_file)
    
    if uploaded_file is not None:
        st.image(image, caption="原始图片", use_container_width=True)
        
        # 图片信息
        st.caption(f"尺寸: {image.size[0]}x{image.size[1]}")

with col2:
    st.subheader("🔍 检测结果")
    
    if uploaded_file is not None:
        # 加载模型
        with st.spinner(f"加载模型 {selected_model_name}..."):
            model, loaded = load_yolo_model(model_path)
        
        if not loaded:
            st.error(f"无法加载模型: {model_path}")
            st.info("请检查模型文件是否存在")
        elif model is not None:
            # 执行检测
            with st.spinner("正在检测..."):
                annotated_img, detections = classify_image(
                    image, model, confidence_threshold
                )
            
            if annotated_img is not None:
                # 显示检测结果
                st.image(annotated_img, caption="检测结果", use_container_width=True)
                
                # 显示统计
                st.markdown("### 📊 检测统计")
                if len(detections) > 0:
                    st.success(f"检测到 **{len(detections)}** 个目标")
                    
                    # 分类统计
                    class_counts = {}
                    for det in detections:
                        cls = det['class_name']
                        class_counts[cls] = class_counts.get(cls, 0) + 1
                    
                    if class_counts:
                        st.write("**类别分布:**")
                        for cls, count in class_counts.items():
                            # 如果是路面缺陷代码，显示中文名称
                            chinese_name = defect_types.get(cls, cls)
                            st.write(f"- {cls} ({chinese_name}): {count}个")
                    
                    # 详细信息
                    with st.expander("查看详细信息"):
                        for i, det in enumerate(detections, 1):
                            chinese_name = defect_types.get(det['class_name'], det['class_name'])
                            st.write(f"**{i}. {det['class_name']} ({chinese_name})**")
                            st.write(f"- 置信度: {det['confidence']:.2%}")
                            st.write(f"- 位置: {det['bbox']}")
                else:
                    st.info("未检测到目标")

# 训练模型部分
st.markdown("---")
st.header("🎓 训练路面缺陷专用模型")

with st.expander("📖 查看训练说明"):
    st.markdown("""
    ### 训练步骤
    
    #### 1. 下载数据集
    - 数据集: N-RDD2024 (Road Damage Dataset)
    - 位置: `Road-Damage-and-Defect-Recognition-Model/` 目录中查看链接
    - 格式: YOLO格式 (.txt标注文件)
    
    #### 2. 准备数据
    ```
    datasets/n_rdd2024/
    ├── images/
    │   ├── train/
    │   └── val/
    └── labels/
        ├── train/
        └── val/
    ```
    
    #### 3. 运行训练
    ```bash
    python train_road_damage_yolov8.py
    ```
    
    #### 4. 使用训练好的模型
    - 将 `best.pt` 复制到 `models/road_damage_yolov8.pt`
    - 刷新页面并选择"路面缺陷专用模型"
    
    ### 或者使用预训练模型
    
    从Roboflow Universe下载:
    1. 访问: https://universe.roboflow.com/
    2. 搜索: "road damage detection yolov8"
    3. 下载 .pt 文件
    4. 放置到 `models/` 目录
    """)

# 底部信息
st.markdown("---")
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.metric("当前模型", selected_model_name.split()[0])
    
with col_b:
    model_status = "✅ 可用" if model_exists or "通用" in selected_model_name else "❌ 未找到"
    st.metric("模型状态", model_status)

with col_c:
    st.metric("置信度阈值", f"{confidence_threshold:.2f}")

# 页脚
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>路面缺陷检测系统 v1.0 | 基于YOLOv8 | 
    <a href="https://github.com/Gabi-comm/Road-Damage-and-Defect-Recognition-Model" target="_blank">数据集来源</a>
    </p>
</div>
""", unsafe_allow_html=True)
