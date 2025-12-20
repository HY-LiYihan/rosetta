import streamlit as st
import json
import os
from openai import OpenAI
from datetime import datetime

# 页面配置
st.set_page_config(
    page_title="语言学概念标注工具",
    page_icon="📝",
    layout="wide"
)

# 自定义CSS调整侧边栏宽度
st.markdown("""
<style>
    /* 调整侧边栏宽度 */
    section[data-testid="stSidebar"] {
        width: 400px !important;
        min-width: 400px !important;
        max-width: 400px !important;
    }
    
    /* 调整主内容区域宽度 */
    .main .block-container {
        padding-left: 420px;
        padding-right: 2rem;
    }
    
    /* 调整小屏幕下的布局 */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            width: 300px !important;
            min-width: 300px !important;
            max-width: 300px !important;
        }
        
        .main .block-container {
            padding-left: 320px;
        }
    }
</style>
""", unsafe_allow_html=True)

# 初始化session state
if "concepts" not in st.session_state:
    with open("concepts.json", "r", encoding="utf-8") as f:
        st.session_state.concepts = json.load(f)["concepts"]

if "annotation_history" not in st.session_state:
    st.session_state.annotation_history = []

if "kimi_api_key" not in st.session_state:
    st.session_state.kimi_api_key = ""

# 保存概念到文件
def save_concepts():
    data = {"concepts": st.session_state.concepts}
    with open("concepts.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 侧边栏 - API设置和概念管理
with st.sidebar:
    st.title("⚙️ 设置")
    
    # API设置
    st.subheader("API配置")
    api_key = st.text_input(
        "Kimi API Key",
        type="password",
        value=st.session_state.kimi_api_key,
        help="请输入Kimi API密钥，可从 https://platform.moonshot.cn/console/api-keys 获取"
    )
    if api_key:
        st.session_state.kimi_api_key = api_key
    
    # 概念管理
    st.subheader("📚 概念管理")
    
    # 显示现有概念
    concept_names = [c["name"] for c in st.session_state.concepts]
    selected_concept_name = st.selectbox(
        "选择概念",
        concept_names,
        help="选择要查看或编辑的概念"
    )
    
    selected_concept = next(c for c in st.session_state.concepts if c["name"] == selected_concept_name)
    
    with st.expander("编辑概念", expanded=False):
        new_name = st.text_input("概念名称", value=selected_concept["name"])
        new_prompt = st.text_area("提示词", value=selected_concept["prompt"], height=100)
        new_category = st.text_input("分类", value=selected_concept.get("category", ""))
        
        st.subheader("标注样例")
        examples = selected_concept.get("examples", [])
        
        for i, example in enumerate(examples):
            col1, col2 = st.columns(2)
            with col1:
                new_text = st.text_area(f"样例{i+1}文本", value=example["text"], key=f"text_{selected_concept_name}_{i}")
            with col2:
                new_annotation = st.text_area(f"样例{i+1}标注", value=example["annotation"], key=f"ann_{selected_concept_name}_{i}")
            
            if new_text != example["text"] or new_annotation != example["annotation"]:
                example["text"] = new_text
                example["annotation"] = new_annotation
        
        # 添加新样例
        add_example_clicked = st.button("添加样例", key=f"add_example_{selected_concept_name}")
        
        # 删除样例
        delete_example_clicked = False
        if len(examples) > 0:
            delete_example_clicked = st.button("删除最后一个样例", key=f"del_example_{selected_concept_name}")
        
        # 保存修改
        save_clicked = st.button("保存修改", key=f"save_{selected_concept_name}")
        
        # 处理按钮点击
        if add_example_clicked:
            examples.append({"text": "", "annotation": ""})
            st.rerun()
        
        if delete_example_clicked and len(examples) > 0:
            examples.pop()
            st.rerun()
        
        if save_clicked:
            selected_concept["name"] = new_name
            selected_concept["prompt"] = new_prompt
            selected_concept["category"] = new_category
            selected_concept["examples"] = examples
            save_concepts()
            st.success("概念已更新！")
            st.rerun()
    
    # 添加新概念
    with st.expander("添加新概念", expanded=False):
        new_concept_name = st.text_input("新概念名称")
        new_concept_prompt = st.text_area("新概念提示词", height=100)
        new_concept_category = st.text_input("新概念分类")
        
        if st.button("添加概念"):
            if new_concept_name and new_concept_prompt:
                new_concept = {
                    "name": new_concept_name,
                    "prompt": new_concept_prompt,
                    "examples": [],
                    "category": new_concept_category,
                    "is_default": False
                }
                st.session_state.concepts.append(new_concept)
                save_concepts()
                st.success(f"概念 '{new_concept_name}' 已添加！")
                st.rerun()
            else:
                st.warning("请至少填写概念名称和提示词")

# 主界面
st.title("📝 语言学概念标注工具")
st.markdown("使用大模型辅助标注语言学概念，如projection、agreement等")

# 概念选择
col1, col2 = st.columns([2, 1])
with col1:
    selected_concept_name = st.selectbox(
        "选择要标注的概念",
        [c["name"] for c in st.session_state.concepts],
        key="main_concept_select"
    )

selected_concept = next(c for c in st.session_state.concepts if c["name"] == selected_concept_name)

# 显示概念信息
with st.expander("查看概念详情", expanded=True):
    st.markdown(f"**概念**: {selected_concept['name']}")
    st.markdown(f"**分类**: {selected_concept.get('category', '未分类')}")
    st.markdown(f"**提示词**: {selected_concept['prompt']}")
    
    st.markdown("**标注样例**:")
    for i, example in enumerate(selected_concept.get("examples", [])):
        st.markdown(f"{i+1}. 文本: `{example['text']}`")
        st.markdown(f"   标注: {example['annotation']}")

# 标注界面
st.divider()
st.subheader("🔍 文本标注")

input_text = st.text_area(
    "输入要标注的文本",
    height=150,
    placeholder="请输入需要标注的文本...",
    help="输入需要分析的语言学文本"
)

if st.button("开始标注", type="primary") and input_text:
    if not st.session_state.kimi_api_key:
        st.error("请先在侧边栏输入Kimi API Key")
    else:
        with st.spinner("正在调用大模型进行标注..."):
            try:
                # 构建提示词
                prompt = f"""你是一个语言学标注助手。请根据以下概念进行文本标注：

概念：{selected_concept['name']}
定义：{selected_concept['prompt']}

标注示例："""
                
                for i, example in enumerate(selected_concept.get("examples", [])):
                    prompt += f"\n{i+1}. 文本：\"{example['text']}\"\n   标注：\"{example['annotation']}\""
                
                prompt += f"""

现在请标注以下文本：
文本：\"{input_text}\"

请提供标注结果（使用**加粗**标记标注内容）："""
                
                # 调用Kimi API
                client = OpenAI(
                    api_key=st.session_state.kimi_api_key,
                    base_url="https://api.moonshot.cn/v1"
                )
                
                response = client.chat.completions.create(
                    model="moonshot-v1-8k",
                    messages=[
                        {"role": "system", "content": "你是一个专业的语言学助手，擅长文本标注和分析。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                annotation_result = response.choices[0].message.content
                
                # 保存到历史记录
                history_entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "concept": selected_concept['name'],
                    "text": input_text,
                    "annotation": annotation_result
                }
                st.session_state.annotation_history.insert(0, history_entry)
                
                # 显示结果
                st.success("标注完成！")
                st.subheader("标注结果")
                st.markdown(annotation_result)
                
                # 复制按钮
                st.code(annotation_result, language="markdown")
                
            except Exception as e:
                st.error(f"标注失败：{str(e)}")

# 历史记录
if st.session_state.annotation_history:
    st.divider()
    st.subheader("📜 标注历史")
    
    for i, entry in enumerate(st.session_state.annotation_history[:5]):  # 显示最近5条
        with st.expander(f"{entry['timestamp']} - {entry['concept']}"):
            st.markdown(f"**文本**: {entry['text']}")
            st.markdown(f"**标注**: {entry['annotation']}")
            
            # 删除按钮
            if st.button(f"删除", key=f"delete_{i}"):
                st.session_state.annotation_history.pop(i)
                st.rerun()

# 页脚
st.divider()
st.caption("语言学概念标注工具 v1.0 | 使用Kimi大模型进行标注")
