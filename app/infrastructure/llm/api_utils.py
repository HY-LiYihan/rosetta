import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from app.infrastructure.llm.registry import get_platform_configs, get_provider
from app.services.platform_service import (
    get_chat_response as service_get_chat_response,
    probe_available_platforms_from_secrets,
)

# Platform config dict exposed for compatibility with legacy UI code.
PLATFORM_CONFIG = get_platform_configs()


def get_client(platform, api_key):
    """Get platform client (compatibility helper)."""
    provider = get_provider(platform)
    if provider is None:
        return None
    return provider.get_client(api_key)


def probe_available_platforms():
    """
    Probe available platforms from st.secrets.
    Return: dict {platform_id: {"name": str, "models": list, "api_key": str}}
    """
    try:
        return probe_available_platforms_from_secrets(st.secrets)
    except StreamlitSecretNotFoundError:
        # Local/dev mode may not provide secrets.toml; treat as no configured platforms.
        return {}


def get_chat_response(platform, api_key, model, messages, temperature=0.3):
    """Unified chat API for annotation flow."""
    return service_get_chat_response(
        platform=platform,
        api_key=api_key,
        model=model,
        messages=messages,
        temperature=temperature,
    )
