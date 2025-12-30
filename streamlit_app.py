import streamlit as st

# 页面配置
st.set_page_config(
    page_title="Rosetta - 智能标注系统",
    page_icon="assets/rosetta-icon-whiteback.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS - 简洁清新的界面设计
st.markdown("""
<style>
    /* ==================== 颜色变量定义 ==================== */
    :root {
        /* 核心品牌色 */
        --color-primary: #E6FFFA;      /* 主色：非常浅的青色，用于标题和重要元素 */
        --color-secondary: #63B3ED;    /* 辅助色：中等蓝色，用于次要元素和悬停效果 */
        --color-accent: #00B4CB;       /* 强调色：青色，用于强调和特殊状态 */
        
        /* 按钮专用色 */
        --color-button: #2C5282;       /* 主要按钮常态色：深蓝色 */
        --color-button-secondary: #2A4365; /* 普通按钮常态色：更深的蓝色 */
        --color-button-hover: #4299E1; /* 按钮悬停色：亮蓝色 */
        
        /* 背景色 */
        --color-bg: #161b22;           /* 主背景色：深灰色 */
        --color-bg-sec: #2D3748;       /* 次要背景色：中灰色（侧边栏） */
        
        /* 界面元素色 */
        --color-card: #2B474B;         /* 卡片背景色：青灰色 */
        --color-text: #F7FAFC;         /* 文字颜色：浅灰色 */
        --color-text-secondary: #A0AEC0;   /* 按钮文字颜色：白色 */
    }
    
    /* 确保侧边栏收回按钮一直显示 */
    section[data-testid="stSidebar"] > div:first-child {
        display: block !important;
    }
    
    /* 侧边栏收回按钮样式 */
    button[data-testid="baseButton-header"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    
    /* 页面主体背景 */
    .stApp {
        background-color: var(--color-bg) !important;
    }
    
    /* 主内容区域背景 */
    .main .block-container {
        background-color: var(--color-bg) !important;
    }
    
    /* 侧边栏样式 */
    section[data-testid="stSidebar"] {
        background-color: var(--color-bg-sec) !important;
        color: var(--color-text) !important;
    }
    
    /* 侧边栏文本颜色 */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stTextInput label,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stButton button {
        color: var(--color-text) !important;
    }
    
    /* 增大侧边栏页面链接字号到22px - 使用稳定的选择器方案 */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
        font-size: 18px !important;
        font-weight: 500 !important;
        padding: 12px 16px !important;
        margin: 4px 0 !important;
        border-radius: 6px !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        align-items: center !important;
        text-decoration: none !important;
        color: var(--color-text) !important; /* 直接在链接上设置文字颜色 */
    }
    
    /* 确保链接内的所有文字元素继承样式 */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] * {
        color: inherit !important;
        font-size: inherit !important;
        font-weight: inherit !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
        background-color: rgba(136, 212, 225, 0.1) !important;
        color: var(--color-primary) !important; /* 悬停时改变文字颜色 */
    }
    
    /* 当前页面链接样式 */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {
        background-color: rgba(136, 212, 225, 0.15) !important;
        color: var(--color-primary) !important;
        font-weight: 600 !important;
    }
    
    /* 侧边栏输入框样式 */
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: var(--color-text) !important;
        border-radius: 6px !important;
    }
    
    /* 侧边栏扩展器样式 */
    section[data-testid="stSidebar"] .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: var(--color-text) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    section[data-testid="stSidebar"] .streamlit-expanderContent {
        background-color: rgba(255, 255, 255, 0.02) !important;
    }
    
    /* 主内容区域 */
    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1200px;
    }
    
    /* 标题样式 */
    h1 {
        color: var(--color-primary) !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
        border-bottom: 2px solid var(--color-accent);
        padding-bottom: 0.5rem;
    }
    
    h2 {
        color: var(--color-secondary) !important;
        font-weight: 600 !important;
        margin-top: 1.5rem !important;
    }
    
    h3 {
        color: var(--color-accent) !important;
        font-weight: 500 !important;
    }
    
    /* 按钮样式 - 纯色设计 */
    .stButton button {
        background-color: var(--color-button-secondary) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton button:hover {
        background-color: var(--color-button-hover) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 8px rgba(143, 172, 192, 0.3) !important;
    }
    
    /* 主要按钮样式 */
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: var(--color-button) !important;
        font-size: 1rem !important;
        padding: 0.6rem 1.8rem !important;
    }
    
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background-color: var(--color-button-hover) !important;
        box-shadow: 0 2px 8px rgba(210, 228, 241, 0.3) !important;
    }
    
    /* 下载按钮样式 - 确保与主要按钮一致 */
    div[data-testid="stDownloadButton"] button {
        background-color: var(--color-button) !important;
        font-size: 1rem !important;
        padding: 0.6rem 1.8rem !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    div[data-testid="stDownloadButton"] button:hover {
        background-color: var(--color-button-hover) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 8px rgba(143, 172, 192, 0.3) !important;
    }
    
    /* 表单提交按钮样式 - 确保与主要按钮一致 */
    div[data-testid="stFormSubmitButton"] button {
        background-color: var(--color-button) !important;
        font-size: 1rem !important;
        padding: 0.6rem 1.8rem !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    div[data-testid="stFormSubmitButton"] button:hover {
        background-color: var(--color-button-hover) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 8px rgba(143, 172, 192, 0.3) !important;
    }
    
    /* 普通表单提交按钮（非主要）样式 */
    div[data-testid="stFormSubmitButton"] button:not([kind="primary"]) {
        background-color: var(--color-button-secondary) !important;
    }
    
    div[data-testid="stFormSubmitButton"] button:not([kind="primary"]):hover {
        background-color: var(--color-button-hover) !important;
    }
    
    /* 文本区域样式 */
    .stTextArea textarea {
        border-radius: 6px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        transition: border-color 0.2s ease !important;
    }
    
    .stTextArea textarea:focus {
        border-color: var(--color-primary) !important;
        box-shadow: 0 0 0 1px rgba(210, 228, 241, 0.1) !important;
    }
    
    /* 卡片/扩展器样式 */
    .streamlit-expanderHeader {
        background-color: var(--color-card) !important;
        border-radius: 6px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        font-weight: 500 !important;
    }
    
    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px !important;
        padding: 8px 16px !important;
        background-color: var(--color-card) !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--color-primary) !important;
        color: white !important;
    }
    
    /* 成功/警告/错误消息样式 */
    .stAlert {
        border-radius: 6px !important;
        border-left: 4px solid !important;
    }
    
    .stAlert.success {
        border-left-color: var(--color-accent) !important;
    }
    
    .stAlert.warning {
        border-left-color: #ffb74d !important;
    }
    
    .stAlert.error {
        border-left-color: #ef5350 !important;
    }
    
    .stAlert.info {
        border-left-color: var(--color-primary) !important;
    }
    
    /* 分隔线 */
    hr {
        margin: 1.5rem 0 !important;
        border: none !important;
        height: 1px !important;
        background-color: rgba(255, 255, 255, 0.2) !important;
    }
    
    /* 页脚样式 */
    .stCaption {
        text-align: center !important;
        color: var(--color-text) !important;
        font-size: 0.85rem !important;
        margin-top: 1.5rem !important;
        padding-top: 1rem !important;
        border-top: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    
    /* 滚动条样式 */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1 !important;
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--color-primary) !important;
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--color-secondary) !important;
    }
    
    /* 小屏幕响应式调整 */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            width: 280px !important;
            min-width: 280px !important;
            max-width: 280px !important;
        }
        
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        /* 移动端侧边栏字号稍小 */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            font-size: 18px !important;
            padding: 10px 14px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# 使用新的Streamlit导航API
# 定义页面
home_page = st.Page(
    "pages/Home.py",
    title="首页",
    icon="🏠",
    default=True  # 设置为默认页面
)

concept_management_page = st.Page(
    "pages/Concept_Management.py",
    title="概念管理",
    icon="📚"
)

annotation_page = st.Page(
    "pages/Annotation.py",
    title="智能标注",
    icon="✏️"
)

# 设置导航
navigation = st.navigation(
    pages=[home_page, concept_management_page, annotation_page],
    position="sidebar",
    expanded=True
)

# 运行选中的页面
navigation.run()
