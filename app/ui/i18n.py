from __future__ import annotations

import streamlit as st

LANGUAGE_KEY = "rosetta_ui_language"

LANGUAGES = {
    "zh-CN": "中文",
    "en-US": "English",
}

TEXT = {
    "zh-CN": {
        "app_title": "Rosetta 标注工具",
        "dashboard": "工作台",
        "concept_lab": "概念实验室",
        "batch_run": "批量标注",
        "review_queue": "审核队列",
        "export_view": "导出与可视化",
        "settings": "设置",
        "language": "语言",
        "advanced_tools": "高级工具",
        "corpus_builder": "语料生成器",
    },
    "en-US": {
        "app_title": "Rosetta Annotation Tool",
        "dashboard": "Dashboard",
        "concept_lab": "Concept Lab",
        "batch_run": "Batch Run",
        "review_queue": "Review Queue",
        "export_view": "Export & View",
        "settings": "Settings",
        "language": "Language",
        "advanced_tools": "Advanced Tools",
        "corpus_builder": "Corpus Builder",
    },
}


def init_language() -> str:
    if LANGUAGE_KEY not in st.session_state:
        st.session_state[LANGUAGE_KEY] = "zh-CN"
    return str(st.session_state[LANGUAGE_KEY])


def set_language(language: str) -> None:
    st.session_state[LANGUAGE_KEY] = language if language in LANGUAGES else "zh-CN"


def get_language() -> str:
    return init_language()


def t(key: str) -> str:
    language = get_language()
    return TEXT.get(language, TEXT["zh-CN"]).get(key, key)
