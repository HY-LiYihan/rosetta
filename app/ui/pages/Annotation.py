import streamlit as st
import streamlit.components.v1 as components
import json
from collections import Counter
from app.infrastructure.llm.api_utils import (
    probe_available_platforms,
)
from app.domain.annotation_format import extract_annotation_tokens
from app.domain.annotation_doc import spans_to_legacy_string
from app.services.annotation_service import (
    build_history_export_filename,
    build_history_export_json,
)
from app.services.annotation_flow_service import run_annotation
from app.state.session_state import (
    ensure_available_config,
    ensure_core_state,
    ensure_platform_selection,
)
from app.state.keys import (
    ANNOTATION_HISTORY,
    AVAILABLE_CONFIG,
    CONCEPTS,
    MODEL_SELECTOR,
    PLATFORM_SELECTOR,
    REUSE_TEXT,
    SELECTED_MODEL,
    SELECTED_PLATFORM,
)
from app.ui.viewmodels.annotation_visualization import annotation_to_colored_html


def _annotation_tokens(annotation) -> list[dict]:
    if isinstance(annotation, dict):
        return [{"text": s["text"], "label": s["label"], "implicit": s["implicit"]}
                for s in annotation.get("layers", {}).get("spans", [])]
    return extract_annotation_tokens(annotation)


def _annotation_display_str(annotation) -> str:
    if isinstance(annotation, dict):
        return spans_to_legacy_string(annotation.get("layers", {}).get("spans", []))
    return annotation or ""


def _render_json_copy_button(json_text: str) -> None:
    payload = json.dumps(json_text)
    components.html(
        f"""
<div style="margin:0.25rem 0 0.75rem 0;">
  <button id="copy-json-btn" style="
    border:1px solid #88D4E1;
    background:#FFFFFF;
    color:#0f172a;
    border-radius:0.4rem;
    padding:0.35rem 0.7rem;
    font-size:0.85rem;
    cursor:pointer;
  ">📋 复制完整 JSON</button>
  <span id="copy-json-status" style="margin-left:0.5rem;color:#88D4E1;font-size:0.82rem;"></span>
</div>
<script>
const text = {payload};
const btn = document.getElementById("copy-json-btn");
const status = document.getElementById("copy-json-status");
btn.onclick = async () => {{
  try {{
    await navigator.clipboard.writeText(text);
    status.textContent = "已复制 / Copied";
  }} catch (e) {{
    status.textContent = "复制失败，请手动复制";
  }}
}};
</script>
""",
        height=54,
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
if AVAILABLE_CONFIG not in st.session_state:
    with st.spinner("正在探测可用 AI 平台..."):
        ensure_available_config(probe_available_platforms)

# 初始化默认平台和模型
ensure_platform_selection(preferred_platform="deepseek")

# 侧边栏 - API设置
with st.sidebar:
    st.title("⚙️ API设置")
    
    # API设置
    st.subheader("API配置")
    
    if not st.session_state[AVAILABLE_CONFIG]:
        st.warning("⚠️ 未探测到可用平台，请在 `secrets.toml` 中配置 API Key")
        selected_platform = None
        selected_model = None
    else:
        # 平台选择
        platform_options = list(st.session_state[AVAILABLE_CONFIG].keys())
        
        # 查找默认索引（优先 DeepSeek）
        default_index = 0
        if "deepseek" in platform_options:
            default_index = platform_options.index("deepseek")
            
        # 平台切换回调：自动切换到该平台的默认模型
        def on_platform_change():
            new_platform = st.session_state[PLATFORM_SELECTOR]
            if new_platform in st.session_state[AVAILABLE_CONFIG]:
                config = st.session_state[AVAILABLE_CONFIG][new_platform]
                st.session_state[SELECTED_PLATFORM] = new_platform
                st.session_state[SELECTED_MODEL] = config["default_model"]

        selected_platform = st.selectbox(
            "选择AI平台",
            platform_options,
            index=default_index if st.session_state[SELECTED_PLATFORM] not in platform_options else platform_options.index(st.session_state[SELECTED_PLATFORM]),
            format_func=lambda x: st.session_state[AVAILABLE_CONFIG][x]["name"],
            key=PLATFORM_SELECTOR,
            on_change=on_platform_change,
            help="仅显示当前网站已配置且验证成功的平台"
        )
        # 确保同步
        st.session_state[SELECTED_PLATFORM] = selected_platform
        
        # 模型选择
        config = st.session_state[AVAILABLE_CONFIG][selected_platform]
        model_options = config["models"]
        
        # 如果当前选中的模型不在该平台的可用列表中，或者刚刚切换了平台（由回调处理），则使用默认模型
        if st.session_state[SELECTED_MODEL] not in model_options:
            st.session_state[SELECTED_MODEL] = config["default_model"]

        selected_model = st.selectbox(
            "选择模型",
            model_options,
            index=model_options.index(st.session_state[SELECTED_MODEL]) if st.session_state[SELECTED_MODEL] in model_options else 0,
            key=MODEL_SELECTOR,
            help=f"动态获取的 {config['name']} 平台模型列表"
        )
        st.session_state[SELECTED_MODEL] = selected_model
    
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

if not st.session_state[CONCEPTS]:
    st.warning("暂无可用概念，请先添加概念")
    if st.button("前往概念管理页面"):
        st.switch_page("app/ui/pages/Concept_Management.py")
else:
    selected_concept_name = st.selectbox(
        "选择要标注的概念",
        [c["name"] for c in st.session_state[CONCEPTS]],
        key="annotation_concept_select"
    )

    selected_concept = next(c for c in st.session_state[CONCEPTS] if c["name"] == selected_concept_name)

    # 显示概念信息
    with st.expander("查看概念详情", expanded=False):
        st.markdown(f"**概念**: {selected_concept['name']}")
        st.markdown(f"**分类**: {selected_concept.get('category', '未分类')}")
        st.markdown(f"**提示词**: {selected_concept['prompt']}")
        
        if selected_concept.get("examples"):
            st.markdown("**标注样例**:")
            for i, example in enumerate(selected_concept.get("examples", [])):
                st.markdown(f"{i+1}. **文本**: `{example['text']}`")
                annotation_html = annotation_to_colored_html(example.get("annotation", ""))
                st.markdown(
                    f"   **标注**: <span style='line-height:1.8'>{annotation_html}</span>",
                    unsafe_allow_html=True,
                )
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
        if not st.session_state[SELECTED_PLATFORM]:
            st.error("没有可用的 AI 平台，请检查 secrets.toml 配置")
        else:
            with st.spinner(f"正在通过 {st.session_state[AVAILABLE_CONFIG][st.session_state[SELECTED_PLATFORM]]['name']} 进行标注..."):
                try:
                    flow_result = run_annotation(
                        concept=selected_concept,
                        input_text=input_text,
                        available_config=st.session_state[AVAILABLE_CONFIG],
                        selected_platform=st.session_state[SELECTED_PLATFORM],
                        selected_model=st.session_state[SELECTED_MODEL],
                        temperature=temperature
                    )
                    if not flow_result["ok"]:
                        st.error(flow_result["error"])
                        st.stop()

                    annotation_result = flow_result["raw_result"]
                    parsed_result = flow_result["parsed_result"]
                    if flow_result.get("parse_warning"):
                        st.warning(flow_result["parse_warning"])

                    st.session_state[ANNOTATION_HISTORY].insert(0, flow_result["history_entry"])
                    
                    # 显示结果
                    st.success("标注完成！")
                    st.subheader("📊 标注结果")
                    
                    if parsed_result:
                        st.markdown("**JSON 结果（默认折叠）**")
                        _render_json_copy_button(
                            json.dumps(parsed_result, ensure_ascii=False, indent=2)
                        )
                        st.json(parsed_result, expanded=False)

                        annotation_val = parsed_result.get("annotation", "")
                        tokens = _annotation_tokens(annotation_val)
                        label_counter = Counter(t["label"] for t in tokens)
                        implicit_count = sum(1 for t in tokens if t["implicit"])

                        st.markdown("**标注结果统计：**")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("标注片段数", len(tokens))
                        with col2:
                            st.metric("标签种类", len(label_counter))
                        with col3:
                            st.metric("隐含标注数", implicit_count)

                        st.markdown("**标注可视化：**")
                        visual_html = annotation_to_colored_html(annotation_val)
                        st.markdown(
                            f"<div style='line-height:1.9;font-size:1rem'>{visual_html}</div>",
                            unsafe_allow_html=True,
                        )

                        if label_counter:
                            st.markdown("**标签分布：**")
                            st.dataframe(
                                [{"label": k, "count": v} for k, v in label_counter.items()],
                                use_container_width=True,
                                hide_index=True,
                            )

                        # 显示详细内容
                        with st.expander("查看详细内容", expanded=True):
                            st.markdown(f"**文本：** {parsed_result.get('text', '')}")
                            st.markdown(f"**标注分析：** {_annotation_display_str(annotation_val)}")
                            st.markdown(f"**解释说明：** {parsed_result.get('explanation', '')}")
                    else:
                        # 显示原始响应
                        st.markdown(annotation_result)
                        st.code(annotation_result, language="markdown")
                    
                    # 显示使用的平台和模型信息
                    st.info(f"使用平台：{st.session_state[SELECTED_PLATFORM]} | 模型：{st.session_state[SELECTED_MODEL]} | 温度：{temperature}")
                    
                except Exception as e:
                    st.error(f"标注失败：{str(e)}")

# 历史记录
if st.session_state[ANNOTATION_HISTORY]:
    st.divider()
    history_col, download_col = st.columns([3, 1])
    with history_col:
        st.subheader("📜 标注历史")
    with download_col:
        history_export_json = build_history_export_json(st.session_state[ANNOTATION_HISTORY])
        st.download_button(
            "下载全部历史",
            data=history_export_json,
            file_name=build_history_export_filename(),
            mime="application/json",
            use_container_width=True,
            key="download_annotation_history",
        )
    
    for i, entry in enumerate(st.session_state[ANNOTATION_HISTORY][:5]):  # 显示最近5条
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
                    st.session_state[ANNOTATION_HISTORY].pop(i)
                    st.rerun()
            with col2:
                if st.button(f"重新使用此文本", key=f"reuse_text_{i}"):
                    st.session_state[REUSE_TEXT] = entry['text']
                    st.rerun()

# 检查是否有要重用的文本
if REUSE_TEXT in st.session_state:
    st.rerun()

# 导航按钮
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏠 返回首页", use_container_width=True):
        st.switch_page("app/ui/pages/Home.py")

with col2:
    if st.button("📚 概念管理", use_container_width=True):
        st.switch_page("app/ui/pages/Concept_Management.py")

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
""".format(st.session_state[SELECTED_PLATFORM], st.session_state[SELECTED_MODEL]), unsafe_allow_html=True)
