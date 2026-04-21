from __future__ import annotations

from app.infrastructure.llm.base import PlatformConfig


def _filter_kimi(models: list[str]) -> list[str]:
    return [m for m in models if "moonshot" in m or "kimi" in m]


def _filter_deepseek(models: list[str]) -> list[str]:
    return [m for m in models if "deepseek" in m]


PLATFORM_CONFIGS: dict[str, PlatformConfig] = {
    "deepseek": PlatformConfig(
        platform_id="deepseek",
        name="DeepSeek",
        base_url="https://api.deepseek.com",
        key_name="deepseek_api_key",
        default_model="deepseek-chat",
        model_filter=_filter_deepseek,
    ),
    "kimi": PlatformConfig(
        platform_id="kimi",
        name="Kimi (Moonshot)",
        base_url="https://api.moonshot.cn/v1",
        key_name="kimi_api_key",
        default_model="kimi-k2-thinking",
        model_filter=_filter_kimi,
    ),
    "qwen": PlatformConfig(
        platform_id="qwen",
        name="Qwen (DashScope)",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        key_name="qwen_api_key",
        default_model="qwen-plus",
    ),
    "zhipuai": PlatformConfig(
        platform_id="zhipuai",
        name="Zhipu AI (GLM)",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        key_name="zhipuai_api_key",
        default_model="glm-5",
        chat_extra_body={"thinking": {"type": "disabled"}},
    ),
}
