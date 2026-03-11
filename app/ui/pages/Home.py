import streamlit as st
from app.state.keys import ANNOTATION_HISTORY, CONCEPTS, SELECTED_CONCEPT
from app.state.session_state import ensure_core_state
from app.ui.viewmodels.home_viewmodel import build_home_metrics

# 页面标题
st.title("🏠 Rosetta - 智能语义概念标注系统")

# 应用简介
st.markdown("""
<h3 style='color: var(--color-primary); margin-top: 0;'>欢迎使用 Rosetta</h3>
<p style='color: var(--color-text); line-height: 1.6;'>
    Rosetta 是一个基于大语言模型的智能语义概念标注系统，为语言学研究者、翻译工作者、文学研究者和教育工作者提供高效的概念标注工具。
    系统支持多个 AI 平台，提供智能概念标注、交互式概念管理和数据持久化功能。
</p>
""", unsafe_allow_html=True)

# 初始化共享 session state
ensure_core_state()

# 快速统计卡片
st.subheader("📊 快速统计")

col1, col2, col3 = st.columns(3)

with col1:
    metrics = build_home_metrics(st.session_state[CONCEPTS], st.session_state[ANNOTATION_HISTORY])
    st.metric(
        label="概念数量",
        value=metrics["concept_count"],
        delta=f"{metrics['custom_count']} 个自定义"
    )

with col2:
    st.metric(
        label="标注历史",
        value=metrics["history_count"],
        delta=metrics["history_delta"],
    )

with col3:
    # 计算平均标注长度
    if metrics["history_count"]:
        st.metric(
            label="平均标注长度",
            value=f"{metrics['avg_length']:.0f} 字符",
            delta="字符"
        )
    else:
        st.metric(
            label="平均标注长度",
            value="0 字符",
            delta="暂无数据"
        )

# 功能卡片
st.subheader("🚀 核心功能")

cols = st.columns(3)

with cols[0]:
    st.markdown("""
    <div style='text-align: center; padding: 1.2rem; background-color: var(--color-card); border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.2); height: 100%;'>
        <div style='font-size: 2rem; margin-bottom: 0.8rem;'>🤖</div>
        <h4 style='color: var(--color-primary); margin-bottom: 0.5rem; font-size: 1.1rem; padding-left: 1.1em;'>多模型支持</h4>
        <p style='color: var(--color-text); line-height: 1.4; font-size: 0.9rem;'>支持国内多个大语言模型平台，实时动态获取可用模型</p>
    </div>
    """, unsafe_allow_html=True)

with cols[1]:
    st.markdown("""
    <div style='text-align: center; padding: 1.2rem; background-color: var(--color-card); border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.2); height: 100%;'>
        <div style='font-size: 2rem; margin-bottom: 0.8rem;'>📚</div>
        <h4 style='color: var(--color-primary); margin-bottom: 0.5rem; font-size: 1.1rem; padding-left: 1.1em;'>概念管理</h4>
        <p style='color: var(--color-text); line-height: 1.4; font-size: 0.9rem;'>自定义语言学概念，支持编辑、导入导出，满足不同研究需求</p>
    </div>
    """, unsafe_allow_html=True)

with cols[2]:
    st.markdown("""
    <div style='text-align: center; padding: 1.2rem; background-color: var(--color-card); border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.2); height: 100%;'>
        <div style='font-size: 2rem; margin-bottom: 0.8rem;'>✏️</div>
        <h4 style='color: var(--color-primary); margin-bottom: 0.5rem; font-size: 1.1rem; padding-left: 1.1em;'>智能标注</h4>
        <p style='color: var(--color-text); line-height: 1.4; font-size: 0.9rem;'>利用大语言模型自动标注复杂的语言学概念，提高研究效率</p>
    </div>
    """, unsafe_allow_html=True)

# 最近概念列表
st.subheader("📋 最近使用的概念")

if st.session_state[CONCEPTS]:
    # 显示前5个概念
    for i, concept in enumerate(st.session_state[CONCEPTS][:5]):
        with st.expander(f"{concept['name']} - {concept.get('category', '未分类')}", expanded=False):
            st.markdown(f"**提示词**: {concept['prompt'][:100]}..." if len(concept['prompt']) > 100 else f"**提示词**: {concept['prompt']}")
            st.markdown(f"**样例数量**: {len(concept.get('examples', []))}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"使用此概念标注", key=f"use_concept_{i}"):
                    st.session_state[SELECTED_CONCEPT] = concept['name']
                    st.switch_page("app/ui/pages/Annotation.py")
            with col2:
                if st.button(f"编辑概念", key=f"edit_concept_{i}"):
                    st.switch_page("app/ui/pages/Concept_Management.py")
else:
    st.info("暂无概念，请先添加概念")

# 最近标注历史
if st.session_state[ANNOTATION_HISTORY]:
    st.subheader("📜 最近标注记录")
    
    for i, entry in enumerate(st.session_state[ANNOTATION_HISTORY][:3]):
        with st.expander(f"{entry['timestamp']} - {entry['concept']}", expanded=False):
            st.markdown(f"**平台**: {entry.get('platform', '未知')}")
            st.markdown(f"**文本**: {entry['text'][:100]}..." if len(entry['text']) > 100 else f"**文本**: {entry['text']}")
            st.markdown(f"**标注**: {entry['annotation'][:200]}..." if len(entry['annotation']) > 200 else f"**标注**: {entry['annotation']}")

# 页脚
st.divider()
st.markdown("""
<div style='text-align: center; color: var(--color-text); font-size: 0.9rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.2);'>
    <p><strong>Rosetta - 智能语言学概念标注系统</strong></p>
    <p>版本: v2.1 | 最后更新: 2025年12月30日</p>
    <p>项目地址: <a href='https://github.com/HY-LiYihan/rosetta' target='_blank'>GitHub</a></p>
</div>
""", unsafe_allow_html=True)
