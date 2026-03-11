import json
import logging
import streamlit as st
from app.domain.schemas import DATA_VERSION
from app.domain.validators import normalize_payload

logger = logging.getLogger(__name__)

_DEFAULT_CONCEPT = {
    "name": "默认",
    "prompt": "默认",
    "examples": [
        {
            "text": "默认",
            "annotation": "默认",
            "explanation": "默认",
        }
    ],
    "category": "默认",
    "is_default": True,
}


def load_concepts_from_file(file_path: str = "assets/concepts.json") -> tuple[list[dict], str]:
    """Load concept list and data version from JSON file, fallback to default concept."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        normalized = normalize_payload(payload)
        if normalized["concepts"]:
            return normalized["concepts"], normalized.get("version", DATA_VERSION)
    except FileNotFoundError:
        logger.warning("Concept file not found, fallback to default concept: %s", file_path)
    except Exception as e:
        logger.exception("Failed to load concepts from %s, fallback to default. error=%s", file_path, e)

    return [_DEFAULT_CONCEPT.copy()], DATA_VERSION


def ensure_core_state(file_path: str = "assets/concepts.json") -> None:
    """Ensure shared session state keys required by all pages are initialized."""
    if "concepts" not in st.session_state:
        concepts, version = load_concepts_from_file(file_path)
        st.session_state.concepts = concepts
        st.session_state.concepts_data_version = version

    if "concepts_data_version" not in st.session_state:
        st.session_state.concepts_data_version = DATA_VERSION

    if "annotation_history" not in st.session_state:
        st.session_state.annotation_history = []


def ensure_available_config(probe_func) -> None:
    """Ensure available platform config has been probed once in this session."""
    if "available_config" not in st.session_state:
        st.session_state.available_config = probe_func()


def ensure_platform_selection(preferred_platform: str = "deepseek") -> None:
    """Ensure selected platform/model are initialized from available platform config."""
    available = st.session_state.get("available_config", {})

    if "selected_platform" not in st.session_state:
        if preferred_platform in available:
            st.session_state.selected_platform = preferred_platform
        elif available:
            st.session_state.selected_platform = list(available.keys())[0]
        else:
            st.session_state.selected_platform = None

    if "selected_model" not in st.session_state:
        selected_platform = st.session_state.get("selected_platform")
        if selected_platform and selected_platform in available:
            st.session_state.selected_model = available[selected_platform].get("default_model")
        else:
            st.session_state.selected_model = None
