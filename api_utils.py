import streamlit as st
from app.infrastructure.llm.registry import get_platform_configs, get_provider
from app.services.platform_service import (
    get_chat_response as service_get_chat_response,
    probe_available_platforms_from_secrets,
)

# 各平台的配置信息（兼容保留）
PLATFORM_CONFIG = get_platform_configs()

def get_client(platform, api_key):
    """获取指定平台客户端（兼容保留）"""
    provider = get_provider(platform)
    if provider is None:
        return None
    return provider.get_client(api_key)

def probe_available_platforms():
    """
    根据 st.secrets 探测可用的平台。
    返回: dict {platform_id: {"name": str, "models": list, "api_key": str}}
    """
    return probe_available_platforms_from_secrets(st.secrets)

def get_chat_response(platform, api_key, model, messages, temperature=0.3):
    """统一的对话接口"""
    return service_get_chat_response(
        platform=platform,
        api_key=api_key,
        model=model,
        messages=messages,
        temperature=temperature,
    )
