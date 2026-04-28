import streamlit as st
import sys

from app.infrastructure.config.runtime_flags import parse_runtime_flags
from app.infrastructure.debug import configure_debug, is_debug_mode, log_debug_event
from app.ui.components.debug_notice import render_debug_notice
from app.ui.i18n import LANGUAGES, get_language, init_language, set_language, t

# 页面配置
st.set_page_config(
    page_title="Rosetta 标注工具",
    page_icon="assets/rosetta-icon-whiteback.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_language()

runtime_flags = parse_runtime_flags(sys.argv[1:])
configure_debug(enabled=runtime_flags.debug_mode)
if is_debug_mode():
    log_debug_event("app_entry", {"argv": sys.argv[1:]})
    if not render_debug_notice(countdown_seconds=5):
        st.stop()

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

with st.sidebar:
    st.markdown(f"### {t('app_title')}")
    with st.expander(t("settings"), expanded=False):
        current_language = get_language()
        selected_language = st.selectbox(
            t("language"),
            options=list(LANGUAGES.keys()),
            index=list(LANGUAGES.keys()).index(current_language),
            format_func=lambda key: LANGUAGES[key],
            key="rosetta_language_selector",
        )
        if selected_language != current_language:
            set_language(selected_language)
            st.rerun()
    with st.expander(t("advanced_tools"), expanded=False):
        st.caption(t("corpus_builder"))
        st.caption("高级语料生成能力暂时保留在兼容页面，可通过旧页面文件继续使用。")

# 使用新的 Streamlit 导航 API：默认只展示 5 个主流程页面
home_page = st.Page("app/ui/pages/Home.py", title=t("dashboard"), icon="🏠", default=True)
concept_lab_page = st.Page("app/ui/pages/Concept_Lab.py", title=t("concept_lab"), icon="📚")
batch_run_page = st.Page("app/ui/pages/Batch_Run.py", title=t("batch_run"), icon="✏️")
review_queue_page = st.Page("app/ui/pages/Review_Queue.py", title=t("review_queue"), icon="✅")
export_view_page = st.Page("app/ui/pages/Export_View.py", title=t("export_view"), icon="📦")

navigation = st.navigation(
    pages=[
        home_page,
        concept_lab_page,
        batch_run_page,
        review_queue_page,
        export_view_page,
    ],
    position="sidebar",
    expanded=True,
)

navigation.run()
