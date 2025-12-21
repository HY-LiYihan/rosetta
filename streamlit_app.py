import streamlit as st
import json
import os
from openai import OpenAI
from datetime import datetime

# 页面配置
st.set_page_config(
    page_title="Rosetta - 智能语言学概念标注系统",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS - 简洁清新的界面设计
st.markdown("""
<style>
    /* 颜色变量定义 - 所有颜色都在这里集中管理 */
    :root {
        /* 主色调 */
        --primary-color: #D2E4F1;      /* 主色：青色 */
        --secondary-color: #8FACC0;    /* 辅助色：黑色 */
        --accent-color: #ABEDD8;       /* 强调色：浅绿色 */
        
        /* 背景色 */
        --page-bg: #2F3132;            /* 页面背景色 */
        --sidebar-bg: #17191A;         /* 侧边栏背景色 */
        --card-bg: #818D97;            /* 卡片背景色 */
        --light-bg: #2F3132;           /* 浅色背景（与页面背景相同） */
        --dark-bg: #17191A;            /* 深色背景（与侧边栏相同） */
        
        /* 文字颜色 */
        --text-light: #D9E8F3;         /* 浅色文字（用于深色背景） */
        --text-dark: #A1B9CA;          /* 深色文字（用于浅色背景） */
        --text-card: #495057;          /* 卡片文字颜色 */
        --text-footer: #6c757d;        /* 页脚文字颜色 */
        
        /* 边框和阴影 */
        --border-color: #dee2e6;       /* 边框颜色 */
        --border-light: rgba(255, 255, 255, 0.2);  /* 浅色边框（用于侧边栏） */
        --border-dark: #dfe6e9;        /* 深色边框 */
        
        /* 按钮和交互 */
        --button-hover: #05c592;       /* 按钮悬停色 */
        --button-primary-hover: #43a047; /* 主要按钮悬停色 */
        --shadow-primary: rgba(6, 214, 160, 0.3);  /* 主色阴影 */
        --shadow-accent: rgba(76, 175, 80, 0.3);   /* 强调色阴影 */
        
        /* 状态颜色 */
        --success-color: #C5D4CD;      /* 成功色（使用强调色） */
        --warning-color: #ffb74d;      /* 警告色 */
        --error-color: #ef5350;        /* 错误色 */
        --info-color: #e8f1ed;         /* 信息色（使用主色） */
        
        /* 滚动条 */
        --scrollbar-track: #f1f1f1;    /* 滚动条轨道 */
        --scrollbar-thumb: #e8f1ed;    /* 滚动条滑块 */
        --scrollbar-hover: #000000;    /* 滚动条悬停 */
    }
    
    /* 页面主体背景 */
    .stApp {
        background-color: var(--page-bg) !important;
    }
    
    /* 主内容区域背景 */
    .main .block-container {
        background-color: var(--page-bg) !important;
    }
    
    /* 侧边栏样式 - 简化版本 */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        color: var(--text-light) !important;
    }
    
    /* 侧边栏文本颜色 */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stTextInput label,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stButton button {
        color: var(--text-light) !important;
    }
    
    /* 侧边栏输入框样式 */
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid var(--border-light) !important;
        color: var(--text-light) !important;
        border-radius: 6px !important;
    }
    
    /* 侧边栏扩展器样式 */
    section[data-testid="stSidebar"] .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: var(--text-light) !important;
        border: 1px solid var(--border-light) !important;
    }
    
    section[data-testid="stSidebar"] .streamlit-expanderContent {
        background-color: rgba(255, 255, 255, 0.02) !important;
    }
    
    /* 主内容区域 */
    .main .block-container {
        padding-left: 370px;
        padding-right: 2rem;
        padding-top: 1.5rem;
        max-width: 1200px;
    }
    
    /* 标题样式 */
    h1 {
        color: var(--primary-color) !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
        border-bottom: 2px solid var(--accent-color);
        padding-bottom: 0.5rem;
    }
    
    h2 {
        color: var(--secondary-color) !important;
        font-weight: 600 !important;
        margin-top: 1.5rem !important;
    }
    
    h3 {
        color: var(--accent-color) !important;
        font-weight: 500 !important;
    }
    
    /* 按钮样式 - 纯色设计 */
    .stButton button {
        background-color: var(--primary-color) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton button:hover {
        background-color: var(--button-hover) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 8px var(--shadow-primary) !important;
    }
    
    /* 主要按钮样式 */
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: var(--accent-color) !important;
        font-size: 1rem !important;
        padding: 0.6rem 1.8rem !important;
    }
    
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background-color: var(--button-primary-hover) !important;
        box-shadow: 0 2px 8px var(--shadow-accent) !important;
    }
    
    /* 文本区域样式 */
    .stTextArea textarea {
        border-radius: 6px !important;
        border: 1px solid var(--border-color) !important;
        transition: border-color 0.2s ease !important;
    }
    
    .stTextArea textarea:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 1px rgba(6, 214, 160, 0.1) !important;
    }
    
    /* 卡片/扩展器样式 */
    .streamlit-expanderHeader {
        background-color: var(--light-bg) !important;
        border-radius: 6px !important;
        border: 1px solid var(--border-color) !important;
        font-weight: 500 !important;
    }
    
    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px !important;
        padding: 8px 16px !important;
        background-color: var(--light-bg) !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color) !important;
        color: white !important;
    }
    
    /* 成功/警告/错误消息样式 */
    .stAlert {
        border-radius: 6px !important;
        border-left: 4px solid !important;
    }
    
    .stAlert.success {
        border-left-color: var(--success-color) !important;
    }
    
    .stAlert.warning {
        border-left-color: var(--warning-color) !important;
    }
    
    .stAlert.error {
        border-left-color: var(--error-color) !important;
    }
    
    .stAlert.info {
        border-left-color: var(--info-color) !important;
    }
    
    /* 分隔线 */
    hr {
        margin: 1.5rem 0 !important;
        border: none !important;
        height: 1px !important;
        background-color: var(--border-color) !important;
    }
    
    /* 页脚样式 */
    .stCaption {
        text-align: center !important;
        color: var(--text-footer) !important;
        font-size: 0.85rem !important;
        margin-top: 1.5rem !important;
        padding-top: 1rem !important;
        border-top: 1px solid var(--border-color) !important;
    }
    
    /* 滚动条样式 */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--scrollbar-track) !important;
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--scrollbar-thumb) !important;
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--scrollbar-hover) !important;
    }
    
    /* 小屏幕响应式调整 */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            width: 280px !important;
            min-width: 280px !important;
            max-width: 280px !important;
        }
        
        .main .block-container {
            padding-left: 300px;
            padding-right: 1rem;
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

# 从secrets或session state初始化API密钥和模型配置
if "kimi_api_key" not in st.session_state:
    # 优先使用secrets中的API密钥
    if "kimi_api_key" in st.secrets:
        st.session_state.kimi_api_key = st.secrets["kimi_api_key"]
    else:
        st.session_state.kimi_api_key = ""

if "deepseek_api_key" not in st.session_state:
    # 优先使用secrets中的DeepSeek API密钥
    if "deepseek_api_key" in st.secrets:
        st.session_state.deepseek_api_key = st.secrets["deepseek_api_key"]
    else:
        st.session_state.deepseek_api_key = ""

# 模型配置
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "deepseek-reasoner"

if "selected_platform" not in st.session_state:
    st.session_state.selected_platform = "deepseek"

# 保存概念到文件
def save_concepts():
    data = {"concepts": st.session_state.concepts}
    with open("concepts.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 获取平台模型列表（带缓存）
def get_platform_models(platform, api_key):
    """动态获取指定平台的可用模型列表，带缓存机制"""
    
    # 创建缓存键
    cache_key = f"{platform}_models_{api_key[:10] if api_key else 'no_key'}"
    
    # 检查缓存
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    
    # 默认模型列表（当API调用失败时使用）
    default_models = {
        "kimi": [
            "moonshot-v1-8k", 
            "moonshot-v1-32k", 
            "moonshot-v1-128k",
            "kimi-k2-0905-preview",
            "kimi-k2-0711-preview", 
            "kimi-k2-turbo-preview",
            "kimi-k2-thinking",
            "kimi-k2-thinking-turbo"
        ],
        "deepseek": ["deepseek-reasoner", "deepseek-chat", "deepseek-coder"]
    }
    
    if not api_key:
        # 缓存默认列表
        st.session_state[cache_key] = default_models.get(platform, [])
        return st.session_state[cache_key]
    
    try:
        if platform == "kimi":
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.moonshot.cn/v1"
            )
        elif platform == "deepseek":
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
        else:
            st.session_state[cache_key] = default_models.get(platform, [])
            return st.session_state[cache_key]
        
        # 获取模型列表
        model_list = client.models.list()
        model_ids = [model.id for model in model_list.data]
        
        # 过滤和排序模型ID
        filtered_models = []
        for model_id in model_ids:
            if platform == "kimi" and ("moonshot" in model_id or "kimi-k2" in model_id):
                filtered_models.append(model_id)
            elif platform == "deepseek" and "deepseek" in model_id:
                filtered_models.append(model_id)
        
        # 如果没有获取到模型，使用默认列表
        if not filtered_models:
            st.session_state[cache_key] = default_models.get(platform, [])
            return st.session_state[cache_key]
        
        # 按字母顺序排序
        filtered_models.sort()
        
        # 缓存结果
        st.session_state[cache_key] = filtered_models
        return filtered_models
        
    except Exception as e:
        # 记录错误但不显示警告（在UI中处理）
        print(f"无法获取{platform}模型列表: {str(e)}")
        st.session_state[cache_key] = default_models.get(platform, [])
        return st.session_state[cache_key]

# 侧边栏 - API设置和概念管理
with st.sidebar:
    st.title("⚙️ 设置")
    
    # API设置
    st.subheader("API配置")
    
    # 平台选择
    platform_options = ["kimi", "deepseek"]
    selected_platform = st.selectbox(
        "选择AI平台",
        platform_options,
        index=platform_options.index(st.session_state.selected_platform) if st.session_state.selected_platform in platform_options else 0,
        help="选择要使用的AI平台"
    )
    st.session_state.selected_platform = selected_platform
    
    # 模型选择 - 动态获取模型列表
    if selected_platform == "kimi":
        # 获取当前平台的API密钥
        current_api_key = st.session_state.kimi_api_key
        
        # 动态获取模型列表
        with st.spinner("正在获取Kimi模型列表..."):
            model_options = get_platform_models("kimi", current_api_key)
        
        if model_options:
            # 确保当前选择的模型在可用模型中
            if st.session_state.selected_model not in model_options:
                st.session_state.selected_model = model_options[0]
            
            selected_model = st.selectbox(
                "选择Kimi模型",
                model_options,
                index=model_options.index(st.session_state.selected_model) if st.session_state.selected_model in model_options else 0,
                help="动态获取的Kimi模型列表"
            )
            st.session_state.selected_model = selected_model
        else:
            st.error("无法获取Kimi模型列表，请检查API密钥")
            # 使用默认模型
            st.session_state.selected_model = "moonshot-v1-8k"
        
        # Kimi API密钥配置
        has_kimi_secret = "kimi_api_key" in st.secrets and st.secrets["kimi_api_key"]
        
        if has_kimi_secret:
            st.info("✅ Kimi API Key已从secrets.toml加载")
            # 不显示输入框，直接使用secrets中的密钥
            st.session_state.kimi_api_key = st.secrets["kimi_api_key"]
        else:
            st.warning("⚠️ 未在secrets.toml中找到Kimi API Key")
            api_key = st.text_input(
                "Kimi API Key",
                type="password",
                value=st.session_state.kimi_api_key,
                help="请输入Kimi API密钥，可从 https://platform.moonshot.cn/console/api-keys 获取"
            )
            if api_key:
                st.session_state.kimi_api_key = api_key
    
    elif selected_platform == "deepseek":
        # 获取当前平台的API密钥
        current_api_key = st.session_state.deepseek_api_key
        
        # 动态获取模型列表
        with st.spinner("正在获取DeepSeek模型列表..."):
            model_options = get_platform_models("deepseek", current_api_key)
        
        if model_options:
            # 确保当前选择的模型在可用模型中
            if st.session_state.selected_model not in model_options:
                st.session_state.selected_model = model_options[0]
            
            selected_model = st.selectbox(
                "选择DeepSeek模型",
                model_options,
                index=model_options.index(st.session_state.selected_model) if st.session_state.selected_model in model_options else 0,
                help="动态获取的DeepSeek模型列表"
            )
            st.session_state.selected_model = selected_model
        else:
            st.error("无法获取DeepSeek模型列表，请检查API密钥")
            # 使用默认模型
            st.session_state.selected_model = "deepseek-reasoner"
        
        # DeepSeek API密钥配置
        has_deepseek_secret = "deepseek_api_key" in st.secrets and st.secrets["deepseek_api_key"]
        
        if has_deepseek_secret:
            st.info("✅ DeepSeek API Key已从secrets.toml加载")
            # 不显示输入框，直接使用secrets中的密钥
            st.session_state.deepseek_api_key = st.secrets["deepseek_api_key"]
        else:
            st.warning("⚠️ 未在secrets.toml中找到DeepSeek API Key")
            api_key = st.text_input(
                "DeepSeek API Key",
                type="password",
                value=st.session_state.deepseek_api_key,
                help="请输入DeepSeek API密钥"
            )
            if api_key:
                st.session_state.deepseek_api_key = api_key
    
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

# 主界面 - Rosetta品牌设计
st.markdown("<h1 style='text-align: center; color: #e8f1ed;'> Rosetta</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #1b9aaa; margin-bottom: 2rem;'>智能语言学概念标注系统</h3>", unsafe_allow_html=True)

st.divider()

# 概念选择
st.subheader("🎯 选择标注概念")
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
st.subheader(" 文本标注")

input_text = st.text_area(
    "输入要标注的文本",
    height=150,
    placeholder="请输入需要标注的文本...",
    help="输入需要分析的语言学文本"
)

if st.button("开始标注", type="primary") and input_text:
    # 根据选择的平台检查API密钥
    if st.session_state.selected_platform == "kimi" and not st.session_state.kimi_api_key:
        st.error("请先在侧边栏配置Kimi API Key")
    elif st.session_state.selected_platform == "deepseek" and not st.session_state.deepseek_api_key:
        st.error("请先在侧边栏配置DeepSeek API Key")
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
                
                # 根据平台调用相应的API
                if st.session_state.selected_platform == "kimi":
                    # 调用Kimi API
                    client = OpenAI(
                        api_key=st.session_state.kimi_api_key,
                        base_url="https://api.moonshot.cn/v1"
                    )
                    
                    response = client.chat.completions.create(
                        model=st.session_state.selected_model,
                        messages=[
                            {"role": "system", "content": "你是一个专业的语言学助手，擅长文本标注和分析。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=1000
                    )
                    
                elif st.session_state.selected_platform == "deepseek":
                    # 调用DeepSeek API
                    client = OpenAI(
                        api_key=st.session_state.deepseek_api_key,
                        base_url="https://api.deepseek.com"
                    )
                    
                    response = client.chat.completions.create(
                        model=st.session_state.selected_model,
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
                    "annotation": annotation_result,
                    "platform": st.session_state.selected_platform,
                    "model": st.session_state.selected_model
                }
                st.session_state.annotation_history.insert(0, history_entry)
                
                # 显示结果
                st.success("标注完成！")
                st.subheader("标注结果")
                st.markdown(annotation_result)
                
                # 显示使用的平台和模型信息
                st.info(f"使用平台：{st.session_state.selected_platform} | 模型：{st.session_state.selected_model}")
                
                # 复制按钮
                st.code(annotation_result, language="markdown")
                
            except Exception as e:
                st.error(f"标注失败：{str(e)}")

# 历史记录
if st.session_state.annotation_history:
    st.divider()
    st.subheader("📜 标注历史")
    
    for i, entry in enumerate(st.session_state.annotation_history[:5]):  # 显示最近5条
        with st.expander(f"{entry['timestamp']} - {entry['concept']} ({entry.get('platform', 'kimi')})"):
            st.markdown(f"**平台**: {entry.get('platform', 'deepseek')}")
            st.markdown(f"**模型**: {entry.get('model', 'deepseek-reasoner')}")
            st.markdown(f"**文本**: {entry['text']}")
            st.markdown(f"**标注**: {entry['annotation']}")
            
            # 删除按钮
            if st.button(f"删除", key=f"delete_{i}"):
                st.session_state.annotation_history.pop(i)
                st.rerun()

# 功能简介卡片 - 放在页面下方
st.divider()
st.subheader("✨ 核心功能")

with st.container():
    cols = st.columns(3)
    with cols[0]:
        st.markdown("""
        <div style='text-align: center; padding: 1.2rem; background-color: var(--card-bg); border-radius: 8px; border: 1px solid var(--border-color); height: 100%;'>
            <div style='font-size: 2rem; margin-bottom: 0.8rem;'>🤖</div>
            <h4 style='color: var(--primary-color); margin-bottom: 0.5rem; font-size: 1.1rem;'>多模型支持</h4>
            <p style='color: var(--text-card); line-height: 1.4; font-size: 0.9rem;'>支持Kimi和DeepSeek平台，动态获取可用模型，灵活切换不同AI能力</p>
        </div>
        """, unsafe_allow_html=True)
    with cols[1]:
        st.markdown("""
        <div style='text-align: center; padding: 1.2rem; background-color: var(--card-bg); border-radius: 8px; border: 1px solid var(--border-color); height: 100%;'>
            <div style='font-size: 2rem; margin-bottom: 0.8rem;'>📚</div>
            <h4 style='color: var(--primary-color); margin-bottom: 0.5rem; font-size: 1.1rem;'>概念管理</h4>
            <p style='color: var(--text-card); line-height: 1.4; font-size: 0.9rem;'>自定义语言学概念，支持编辑和扩展，满足不同研究需求</p>
        </div>
        """, unsafe_allow_html=True)
    with cols[2]:
        st.markdown("""
        <div style='text-align: center; padding: 1.2rem; background-color: var(--card-bg); border-radius: 8px; border: 1px solid var(--border-color); height: 100%;'>
            <div style='font-size: 2rem; margin-bottom: 0.8rem;'>🔒</div>
            <h4 style='color: var(--primary-color); margin-bottom: 0.5rem; font-size: 1.1rem;'>安全可靠</h4>
            <p style='color: var(--text-card); line-height: 1.4; font-size: 0.9rem;'>API密钥安全管理，支持Streamlit Secrets，保障数据安全</p>
        </div>
        """, unsafe_allow_html=True)

# 页脚
st.divider()
st.markdown("""
<div style='text-align: center; color: var(--text-footer); font-size: 0.9rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border-color);'>
    <p><strong>🔍 Rosetta - 智能语言学概念标注系统 v2.1</strong></p>
    <p>当前平台: <span style='color: var(--primary-color);'>{}</span> | 当前模型: <span style='color: var(--secondary-color);'>{}</span></p>
    <p>项目地址: <a href='https://github.com/HY-LiYihan/rosetta' target='_blank'>GitHub</a> | 在线演示: <a href='https://rosetta-git.streamlit.app/' target='_blank'>Streamlit Cloud</a></p>
</div>
""".format(st.session_state.selected_platform, st.session_state.selected_model), unsafe_allow_html=True)
