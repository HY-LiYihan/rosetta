import streamlit as st
from app.infrastructure.llm import api_utils
from app.services.annotation_service import (
    build_annotation_prompt,
    build_history_entry,
    parse_annotation_response,
)
from app.state.session_state import (
    ensure_available_config,
    ensure_core_state,
    ensure_platform_selection,
)

# 页面标题
st.title("✏️ 文本标注工具")

st.markdown("""
<p style='color: var(--color-text); line-height: 1.6;'>
    使用此工具进行语言学文本标注。选择概念、输入文本，系统将利用大语言模型自动生成标注结果。
    您可以在侧边栏配置 AI 平台和模型设置。
</p>
""", unsafe_allow_html=True)

# 初始化共享 session state
ensure_core_state()

# 自动探测可用平台
if "available_config" not in st.session_state:
    with st.spinner("正在探测可用 AI 平台..."):
        ensure_available_config(api_utils.probe_available_platforms)

# 初始化默认平台和模型
ensure_platform_selection(preferred_platform="deepseek")

# 侧边栏 - API设置
with st.sidebar:
    st.title("⚙️ API设置")
    
    # API设置
    st.subheader("API配置")
    
    if not st.session_state.available_config:
        st.warning("⚠️ 未探测到可用平台，请在 `secrets.toml` 中配置 API Key")
        selected_platform = None
        selected_model = None
    else:
        # 平台选择
        platform_options = list(st.session_state.available_config.keys())
        
        # 查找默认索引（优先 DeepSeek）
        default_index = 0
        if "deepseek" in platform_options:
            default_index = platform_options.index("deepseek")
            
        # 平台切换回调：自动切换到该平台的默认模型
        def on_platform_change():
            new_platform = st.session_state.platform_selector
            if new_platform in st.session_state.available_config:
                config = st.session_state.available_config[new_platform]
                st.session_state.selected_platform = new_platform
                st.session_state.selected_model = config["default_model"]

        selected_platform = st.selectbox(
            "选择AI平台",
            platform_options,
            index=default_index if st.session_state.selected_platform not in platform_options else platform_options.index(st.session_state.selected_platform),
            format_func=lambda x: st.session_state.available_config[x]["name"],
            key="platform_selector",
            on_change=on_platform_change,
            help="仅显示当前网站已配置且验证成功的平台"
        )
        # 确保同步
        st.session_state.selected_platform = selected_platform
        
        # 模型选择
        config = st.session_state.available_config[selected_platform]
        model_options = config["models"]
        
        # 如果当前选中的模型不在该平台的可用列表中，或者刚刚切换了平台（由回调处理），则使用默认模型
        if st.session_state.selected_model not in model_options:
            st.session_state.selected_model = config["default_model"]

        selected_model = st.selectbox(
            "选择模型",
            model_options,
            index=model_options.index(st.session_state.selected_model) if st.session_state.selected_model in model_options else 0,
            key="model_selector",
            help=f"动态获取的 {config['name']} 平台模型列表"
        )
        st.session_state.selected_model = selected_model
    
    # 温度参数设置
    st.subheader("模型参数")
    temperature = st.slider(
        "温度 (Temperature)",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.1,
        help="控制生成文本的随机性，值越高越有创造性"
    )
    

# 主内容区域
# 概念选择
st.subheader("🎯 选择标注概念")

if not st.session_state.concepts:
    st.warning("暂无可用概念，请先添加概念")
    if st.button("前往概念管理页面"):
        st.switch_page("pages/Concept_Management.py")
else:
    selected_concept_name = st.selectbox(
        "选择要标注的概念",
        [c["name"] for c in st.session_state.concepts],
        key="annotation_concept_select"
    )

    selected_concept = next(c for c in st.session_state.concepts if c["name"] == selected_concept_name)

    # 显示概念信息
    with st.expander("查看概念详情", expanded=False):
        st.markdown(f"**概念**: {selected_concept['name']}")
        st.markdown(f"**分类**: {selected_concept.get('category', '未分类')}")
        st.markdown(f"**提示词**: {selected_concept['prompt']}")
        
        if selected_concept.get("examples"):
            st.markdown("**标注样例**:")
            for i, example in enumerate(selected_concept.get("examples", [])):
                st.markdown(f"{i+1}. **文本**: `{example['text']}`")
                st.markdown(f"   **标注**: {example['annotation']}")
                if "explanation" in example and example["explanation"]:
                    st.markdown(f"   **解释**: {example['explanation']}")
                st.markdown("---")

    # 标注界面
    st.divider()
    st.subheader("📝 文本标注")

    input_text = st.text_area(
        "输入要标注的文本",
        height=150,
        placeholder="请输入需要标注的文本...",
        help="输入需要分析的语言学文本",
        key="annotation_input"
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        annotate_clicked = st.button("开始标注", type="primary", use_container_width=True)
    with col2:
        clear_clicked = st.button("清空输入", use_container_width=True)

    if clear_clicked:
        st.rerun()

    if annotate_clicked and input_text:
        # 检查是否有可用平台
        if not st.session_state.selected_platform:
            st.error("没有可用的 AI 平台，请检查 secrets.toml 配置")
        else:
            with st.spinner(f"正在通过 {st.session_state.available_config[st.session_state.selected_platform]['name']} 进行标注..."):
                try:
                    # 获取当前平台的 Key
                    api_key = st.session_state.available_config[st.session_state.selected_platform]["api_key"]
                    
                    prompt = build_annotation_prompt(selected_concept, input_text)
                    
                    # 调用统一的 API 接口
                    annotation_result = api_utils.get_chat_response(
                        platform=st.session_state.selected_platform,
                        api_key=api_key,
                        model=st.session_state.selected_model,
                        messages=[
                            {"role": "system", "content": "你是一个专业的语言学助手，擅长文本标注和分析。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=temperature
                    )
                    
                    parsed_result, parse_warning = parse_annotation_response(annotation_result)
                    if parse_warning:
                        st.warning(parse_warning)
                    
                    # 保存到历史记录
                    history_entry = build_history_entry(
                        concept_name=selected_concept["name"],
                        input_text=input_text,
                        annotation_result=annotation_result,
                        parsed_result=parsed_result,
                        platform=st.session_state.selected_platform,
                        model=st.session_state.selected_model,
                        temperature=temperature,
                    )
                    st.session_state.annotation_history.insert(0, history_entry)
                    
                    # 显示结果
                    st.success("标注完成！")
                    st.subheader("📊 标注结果")
                    
                    if parsed_result:
                        # 显示格式化后的JSON结果
                        st.json(parsed_result)
                        
                        # 显示结构化信息
                        st.markdown("**结构化信息：**")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("文本", parsed_result.get("text", "")[:50] + "..." if len(parsed_result.get("text", "")) > 50 else parsed_result.get("text", ""))
                        with col2:
                            st.metric("标注类型", "已解析")
                        with col3:
                            st.metric("解释长度", f"{len(parsed_result.get('explanation', ''))} 字符")
                        
                        # 显示详细内容
                        with st.expander("查看详细内容", expanded=True):
                            st.markdown(f"**文本：** {parsed_result.get('text', '')}")
                            st.markdown(f"**标注分析：** {parsed_result.get('annotation', '')}")
                            st.markdown(f"**解释说明：** {parsed_result.get('explanation', '')}")
                    else:
                        # 显示原始响应
                        st.markdown(annotation_result)
                        st.code(annotation_result, language="markdown")
                    
                    # 显示使用的平台和模型信息
                    st.info(f"使用平台：{st.session_state.selected_platform} | 模型：{st.session_state.selected_model} | 温度：{temperature}")
                    
                except Exception as e:
                    st.error(f"标注失败：{str(e)}")

# 历史记录
if st.session_state.annotation_history:
    st.divider()
    st.subheader("📜 标注历史")
    
    for i, entry in enumerate(st.session_state.annotation_history[:5]):  # 显示最近5条
        with st.expander(f"{entry['timestamp']} - {entry['concept']} ({entry.get('platform', '未知')})"):
            st.markdown(f"**平台**: {entry.get('platform', '未知')}")
            st.markdown(f"**模型**: {entry.get('model', '未知')}")
            if 'temperature' in entry:
                st.markdown(f"**温度**: {entry['temperature']}")
            st.markdown(f"**文本**: {entry['text']}")
            
            if entry.get('parsed_result'):
                st.markdown("**解析结果**:")
                st.json(entry['parsed_result'])
            else:
                st.markdown(f"**标注**: {entry['annotation'][:500]}..." if len(entry['annotation']) > 500 else f"**标注**: {entry['annotation']}")
            
            # 删除按钮
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button(f"删除", key=f"delete_annotation_{i}"):
                    st.session_state.annotation_history.pop(i)
                    st.rerun()
            with col2:
                if st.button(f"重新使用此文本", key=f"reuse_text_{i}"):
                    st.session_state.reuse_text = entry['text']
                    st.rerun()

# 检查是否有要重用的文本
if "reuse_text" in st.session_state:
    st.rerun()

# 导航按钮
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏠 返回首页", use_container_width=True):
        st.switch_page("pages/Home.py")

with col2:
    if st.button("📚 概念管理", use_container_width=True):
        st.switch_page("pages/Concept_Management.py")

with col3:
    if st.button("🔄 刷新页面", use_container_width=True):
        st.rerun()

# 页脚
st.divider()
st.markdown("""
<div style='text-align: center; color: var(--color-text); font-size: 0.9rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.2);'>
    <p><strong>文本标注工具</strong> | 当前平台: {} | 当前模型: {}</p>
    <p>提示: 标注历史保存在 session state 中，重启应用后会清空</p>
</div>
""".format(st.session_state.selected_platform, st.session_state.selected_model), unsafe_allow_html=True)
