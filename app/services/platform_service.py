from __future__ import annotations

from app.infrastructure.llm.registry import get_platform_configs, get_provider


def probe_available_platforms_from_secrets(secrets) -> dict:
    """Probe available platforms by validating configured API keys against model listing."""
    available: dict[str, dict] = {}

    for pid, config in get_platform_configs().items():
        key_name = config["key_name"]
        if key_name not in secrets or not secrets[key_name]:
            continue

        api_key = secrets[key_name]
        provider = get_provider(pid)
        if provider is None:
            continue

        try:
            model_ids = provider.list_models(api_key)
            if not model_ids:
                continue

            available[pid] = {
                "name": config["name"],
                "models": model_ids,
                "api_key": api_key,
                "default_model": config["default_model"],
            }
        except Exception:
            continue

    return available


def get_chat_response(platform: str, api_key: str, model: str, messages: list[dict], temperature: float = 0.3) -> str:
    provider = get_provider(platform)
    if provider is None:
        raise ValueError(f"无法创建平台 {platform} 的客户端")

    try:
        return provider.chat(api_key=api_key, model=model, messages=messages, temperature=temperature)
    except Exception as e:
        raise Exception(f"调用 {platform} 失败: {str(e)}")
