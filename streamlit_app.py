import streamlit as st

# 页面配置
st.set_page_config(
    page_title="Rosetta - 智能标注系统",
    page_icon="assets/rosetta-icon-whiteback.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 全局样式策略：优先使用 .streamlit/config.toml 主题配置；
# 这里仅保留 TOML 暂不覆盖的选择器级样式（导航密度、侧边栏按钮可见性、移动端导航细节）。
st.markdown(
    """
<style>
    :root {
        --color-primary: #E6FFFA;
        --color-secondary: #63B3ED;
        --color-accent: #00B4CB;
        --color-card: #2B474B;
        --color-text: #D9E8F3;
        --color-button: #2C5282;
        --color-button-secondary: #2A4365;
        --color-button-hover: #4299E1;
    }

    section[data-testid="stSidebar"] > div:first-child {
        display: block !important;
    }

    button[data-testid="baseButton-header"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }

    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1200px;
    }

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
        color: var(--color-text) !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] * {
        color: inherit !important;
        font-size: inherit !important;
        font-weight: inherit !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
        background-color: rgba(136, 212, 225, 0.1) !important;
        color: var(--color-primary) !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {
        background-color: rgba(136, 212, 225, 0.15) !important;
        color: var(--color-primary) !important;
        font-weight: 600 !important;
    }

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

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            font-size: 18px !important;
            padding: 10px 14px !important;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)

# 使用新的 Streamlit 导航 API
home_page = st.Page("app/ui/pages/Home.py", title="首页", icon="🏠", default=True)
concept_management_page = st.Page("app/ui/pages/Concept_Management.py", title="概念管理", icon="📚")
annotation_page = st.Page("app/ui/pages/Annotation.py", title="智能标注", icon="✏️")

navigation = st.navigation(
    pages=[home_page, concept_management_page, annotation_page],
    position="sidebar",
    expanded=True,
)

navigation.run()
