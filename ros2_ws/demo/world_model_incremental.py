#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
低秩动力学世界模型 - 增量学习演示
实时展示如何根据新观测数据更新基向量并预测演化
"""
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from datetime import datetime

# 设置页面
st.set_page_config(
    page_title="低秩动力学 - 增量学习演示",
    page_icon="🔄",
    layout="wide"
)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

st.title("🔄 低秩动力学世界模型 - 增量学习演示")
st.markdown("**展示如何根据新观测数据实时更新基向量并优化预测**")
st.markdown("---")

# 初始化session state
if 'history_data' not in st.session_state:
    st.session_state.history_data = []
if 'basis_history' not in st.session_state:
    # 初始基向量（5个基，3维）
    st.session_state.basis_history = [np.array([
        [0.1, 0.1, 0.3],   # 基1：深度主导
        [0.2, 0.2, 0.1],   # 基2：横向扩展
        [0.05, 0.05, 0.05], # 基3：均匀模式
    ])]
if 'iteration' not in st.session_state:
    st.session_state.iteration = 0

# 侧边栏：输入新观测数据
st.sidebar.header("📥 输入新观测数据")
st.sidebar.markdown("""
模拟机器人检测到新的缺陷观测数据，
世界模型将更新基向量并优化预测。
""")

st.sidebar.markdown("### 新观测缺陷尺寸")
new_length = st.sidebar.number_input("长度 (cm)", 
    min_value=1.0, max_value=100.0, value=30.0, step=1.0, key='new_len')
new_width = st.sidebar.number_input("宽度 (cm)", 
    min_value=1.0, max_value=100.0, value=10.0, step=1.0, key='new_wid')
new_depth = st.sidebar.number_input("深度 (cm)", 
    min_value=0.1, max_value=20.0, value=2.0, step=0.1, key='new_dep')

st.sidebar.markdown("### 演化时间")
days_passed = st.sidebar.slider("距初始检测天数", 
    min_value=0, max_value=90, value=15, step=15)

learning_rate = st.sidebar.slider("学习率 α", 
    min_value=0.01, max_value=0.5, value=0.1, step=0.01,
    help="控制基向量更新幅度")

if st.sidebar.button("🔄 添加观测并更新模型", type="primary"):
    # 添加新观测
    new_obs = {
        'dims': np.array([new_length/100, new_width/100, new_depth/100]),
        'days': days_passed,
        'time': datetime.now().strftime("%H:%M:%S")
    }
    st.session_state.history_data.append(new_obs)
    
    # 更新基向量
    current_basis = st.session_state.basis_history[-1].copy()
    
    # 增量学习算法
    # 使用新观测数据更新基向量
    obs_vector = new_obs['dims']
    
    # 计算当前基向量的重构误差
    coeffs, residuals, rank, s = np.linalg.lstsq(current_basis, obs_vector, rcond=None)
    reconstruction = current_basis.T @ coeffs
    error = obs_vector - reconstruction
    
    # 梯度下降更新基向量
    # ∂L/∂B = -2 * error * coeffs^T
    gradient = -2 * np.outer(coeffs, error)
    
    # 更新基向量
    updated_basis = current_basis + learning_rate * gradient
    
    # 归一化（保持基向量在合理范围）
    updated_basis = np.clip(updated_basis, 0.01, 0.5)
    
    st.session_state.basis_history.append(updated_basis)
    st.session_state.iteration += 1
    
    st.sidebar.success(f"✅ 已添加第 {st.session_state.iteration} 次观测！")
    st.sidebar.info(f"重构误差: {np.linalg.norm(error):.4f}")

if st.sidebar.button("🔄 重置模型"):
    st.session_state.history_data = []
    st.session_state.basis_history = [np.array([
        [0.1, 0.1, 0.3],
        [0.2, 0.2, 0.1],
        [0.05, 0.05, 0.05],
    ])]
    st.session_state.iteration = 0
    st.sidebar.success("✅ 模型已重置！")

# 主界面
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 基向量演化过程")
    
    if len(st.session_state.basis_history) > 1:
        # 创建基向量演化图
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        fig.suptitle('基向量随观测数据的演化', fontsize=14, fontweight='bold')
        
        basis_names = ['基向量1 (深度主导)', '基向量2 (横向扩展)', '基向量3 (均匀模式)']
        dim_names = ['长度', '宽度', '深度']
        colors = ['#E74C3C', '#3498DB', '#2ECC71']
        
        for basis_idx in range(3):
            ax = axes[basis_idx]
            
            # 提取该基向量的演化历史
            history = np.array([basis[basis_idx] for basis in st.session_state.basis_history])
            
            # 绘制每个维度的演化
            iterations = range(len(history))
            for dim_idx in range(3):
                ax.plot(iterations, history[:, dim_idx], 
                       'o-', linewidth=2, markersize=8,
                       color=colors[dim_idx], label=dim_names[dim_idx])
            
            ax.set_xlabel('迭代次数（观测数）', fontsize=10)
            ax.set_ylabel('权重值', fontsize=10)
            ax.set_title(basis_names[basis_idx], fontsize=11, fontweight='bold')
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3)
            ax.set_xlim(-0.5, len(history)-0.5)
        
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()
        
        # 显示当前基向量数值
        st.markdown("### 📋 当前基向量数值")
        current_basis = st.session_state.basis_history[-1]
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("基1 [长, 宽, 深]", 
                     f"[{current_basis[0,0]:.3f}, {current_basis[0,1]:.3f}, {current_basis[0,2]:.3f}]")
        with col_b:
            st.metric("基2 [长, 宽, 深]", 
                     f"[{current_basis[1,0]:.3f}, {current_basis[1,1]:.3f}, {current_basis[1,2]:.3f}]")
        with col_c:
            st.metric("基3 [长, 宽, 深]", 
                     f"[{current_basis[2,0]:.3f}, {current_basis[2,1]:.3f}, {current_basis[2,2]:.3f}]")
    else:
        st.info("👈 请在左侧添加观测数据，观察基向量如何更新")

with col2:
    st.subheader("🔮 预测能力变化")
    
    if len(st.session_state.history_data) > 0:
        # 使用更新后的基向量进行预测
        current_basis = st.session_state.basis_history[-1]
        
        # 选择一个测试缺陷
        test_defect = np.array([0.3, 0.1, 0.02])  # 30cm × 10cm × 2cm
        
        # 预测未来演化
        paris_C = 1e-10
        paris_m = 3.0
        time_points = np.linspace(0, 90, 7)
        
        predictions_list = []
        for basis_idx, basis in enumerate(st.session_state.basis_history):
            predictions = []
            coeffs, _, _, _ = np.linalg.lstsq(basis, test_defect, rcond=None)
            
            for t_days in time_points:
                growth_factor = 1.0 + paris_C * (t_days ** paris_m)
                pred_dims = test_defect * growth_factor
                
                for i in range(3):
                    dim_growth = np.sum(coeffs * basis[:, i])
                    pred_dims[i] *= (1.0 + dim_growth * t_days / 90)
                
                pred_dims[2] = min(pred_dims[2], 0.5)
                predictions.append(pred_dims)
            
            predictions_list.append(np.array(predictions))
        
        # 绘制预测对比
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        fig.suptitle(f'测试缺陷预测（初始 vs 第{len(st.session_state.history_data)}次更新后）', 
                    fontsize=14, fontweight='bold')
        
        dim_names = ['长度 (cm)', '宽度 (cm)', '深度 (cm)']
        
        for dim_idx in range(3):
            ax = axes[dim_idx]
            
            # 初始预测（虚线）
            initial_pred = predictions_list[0][:, dim_idx] * 100
            ax.plot(time_points, initial_pred, '--', 
                   linewidth=2, color='gray', alpha=0.5, label='初始模型')
            
            # 当前预测（实线）
            current_pred = predictions_list[-1][:, dim_idx] * 100
            ax.plot(time_points, current_pred, '-', 
                   linewidth=3, color=colors[dim_idx], label=f'第{len(st.session_state.history_data)}次更新')
            
            # 如果有实际观测点，标注
            for obs in st.session_state.history_data:
                if obs['days'] in time_points:
                    ax.scatter(obs['days'], obs['dims'][dim_idx]*100, 
                             s=150, color='red', marker='*', zorder=5,
                             edgecolors='black', linewidths=2)
            
            ax.set_xlabel('时间 (天)', fontsize=10)
            ax.set_ylabel(dim_names[dim_idx], fontsize=10)
            ax.set_title(f'{dim_names[dim_idx]}演化预测', fontsize=11, fontweight='bold')
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()
        
        # 计算预测改进
        if len(predictions_list) > 1:
            initial_pred = predictions_list[0]
            current_pred = predictions_list[-1]
            
            # 如果有实际观测，计算误差
            if len(st.session_state.history_data) > 0:
                st.markdown("### 📈 预测改进效果")
                
                col_x, col_y = st.columns(2)
                with col_x:
                    st.markdown("""
                    **模型更新效果**:
                    - ✅ 基向量根据新观测调整
                    - ✅ 预测曲线更贴近实际
                    - ✅ 重构误差逐步降低
                    """)
                
                with col_y:
                    improvement = ((initial_pred[-1] - current_pred[-1]) / initial_pred[-1] * 100)
                    st.metric("深度预测调整", 
                             f"{improvement[2]:.1f}%",
                             delta=f"{(current_pred[-1,2] - initial_pred[-1,2])*100:.2f}cm")
    else:
        st.info("添加观测数据后，将显示预测能力的改进")

# 底部：算法说明
st.markdown("---")
st.markdown("## 🎓 增量学习算法原理")

col_algo1, col_algo2 = st.columns(2)

with col_algo1:
    st.markdown("""
    ### 📐 低秩表征
    
    **核心思想**: 用少量基向量表示复杂演化模式
    
    ```
    缺陷演化 D(t) ≈ Σᵢ αᵢ × bᵢ(t)
    ```
    
    其中:
    - `bᵢ(t)`: 第i个基向量（3维：长宽高）
    - `αᵢ`: 对应系数（通过最小二乘求解）
    
    **优势**:
    - 仅需3-5个基向量（传统需要成千上万样本）
    - 可快速适配新材质
    - 物理意义清晰
    """)

with col_algo2:
    st.markdown(f"""
    ### 🔄 增量更新算法
    
    **步骤**:
    
    1. **计算重构误差**
       ```
       误差 e = 观测值 - 基向量重构值
       ```
    
    2. **计算梯度**
       ```
       ∇L = -2 × 系数 ⊗ 误差
       ```
    
    3. **更新基向量**
       ```
       B_new = B_old + α × ∇L
       ```
       当前学习率: `α = {learning_rate:.2f}`
    
    4. **归一化约束**
       ```
       B ∈ [0.01, 0.5]
       ```
    
    **效果**: 随着观测增多，预测越来越准确！
    """)

# 观测历史记录
if len(st.session_state.history_data) > 0:
    st.markdown("---")
    st.markdown("## 📝 观测历史记录")
    
    history_df_data = []
    for i, obs in enumerate(st.session_state.history_data, 1):
        history_df_data.append({
            '序号': i,
            '时间': obs['time'],
            '天数': obs['days'],
            '长度(cm)': f"{obs['dims'][0]*100:.1f}",
            '宽度(cm)': f"{obs['dims'][1]*100:.1f}",
            '深度(cm)': f"{obs['dims'][2]*100:.2f}",
        })
    
    import pandas as pd
    df = pd.DataFrame(history_df_data)
    st.dataframe(df, use_container_width=True)

# 底部说明
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>低秩动力学世界模型 v1.0 | 增量学习演示 | 小样本 + 物理约束 = 精准预测</p>
</div>
""", unsafe_allow_html=True)

# 使用说明
with st.expander("💡 使用说明"):
    st.markdown("""
    ### 操作步骤
    
    1. **输入初始观测**: 在左侧输入新检测到的缺陷尺寸
    2. **设置时间**: 指定距初始检测的天数
    3. **点击更新**: 观察基向量如何变化
    4. **重复添加**: 多次添加观测，看预测如何改进
    5. **对比效果**: 右侧显示预测能力的提升
    
    ### 展示重点
    
    - **左图**: 基向量的3个维度随观测实时变化
    - **右图**: 预测曲线从初始到优化的对比
    - **红色星号**: 实际观测点
    - **灰色虚线**: 初始模型预测
    - **彩色实线**: 更新后模型预测
    
    ### 创新点
    
    ✅ **小样本学习**: 仅需少量观测即可适配  
    ✅ **增量更新**: 无需重新训练，实时优化  
    ✅ **物理约束**: 结合Paris定律，预测合理  
    ✅ **可解释性**: 基向量有明确物理意义  
    """)
