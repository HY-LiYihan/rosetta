import streamlit as st
from app.domain.schemas import DATA_VERSION
from app.repositories.json_concept_repository import load_concepts_with_fallback
from app.state.keys import (
    ANNOTATION_HISTORY,
    AVAILABLE_CONFIG,
    CONCEPTS,
    CONCEPTS_DATA_VERSION,
    SELECTED_MODEL,
    SELECTED_PLATFORM,
)

def load_concepts_from_file(file_path: str = "assets/concepts.json") -> tuple[list[dict], str]:
    """Load concept list and data version from JSON file, fallback to default concept."""
    return load_concepts_with_fallback(file_path=file_path)


def ensure_core_state(file_path: str = "assets/concepts.json") -> None:
    """Ensure shared session state keys required by all pages are initialized."""
    if CONCEPTS not in st.session_state:
        concepts, version = load_concepts_from_file(file_path)
        st.session_state[CONCEPTS] = concepts
        st.session_state[CONCEPTS_DATA_VERSION] = version

    if CONCEPTS_DATA_VERSION not in st.session_state:
        st.session_state[CONCEPTS_DATA_VERSION] = DATA_VERSION

    if ANNOTATION_HISTORY not in st.session_state:
        st.session_state[ANNOTATION_HISTORY] = []


def ensure_available_config(probe_func) -> None:
    """Ensure available platform config has been probed once in this session."""
    if AVAILABLE_CONFIG not in st.session_state:
        st.session_state[AVAILABLE_CONFIG] = probe_func()


def ensure_platform_selection(preferred_platform: str = "deepseek") -> None:
    """Ensure selected platform/model are initialized from available platform config."""
    available = st.session_state.get(AVAILABLE_CONFIG, {})

    if SELECTED_PLATFORM not in st.session_state:
        if preferred_platform in available:
            st.session_state[SELECTED_PLATFORM] = preferred_platform
        elif available:
            st.session_state[SELECTED_PLATFORM] = list(available.keys())[0]
        else:
            st.session_state[SELECTED_PLATFORM] = None

    if SELECTED_MODEL not in st.session_state:
        selected_platform = st.session_state.get(SELECTED_PLATFORM)
        if selected_platform and selected_platform in available:
            st.session_state[SELECTED_MODEL] = available[selected_platform].get("default_model")
        else:
            st.session_state[SELECTED_MODEL] = None
