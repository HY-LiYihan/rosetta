from __future__ import annotations

from app.infrastructure.llm.registry import get_platform_configs, get_provider


def _safe_read_secret(secrets, key_name: str) -> str | None:
    """Read secret value without assuming secrets backend is initialized."""
    try:
        value = secrets[key_name]
    except Exception:
        return None
    return value if value else None


def probe_available_platforms_from_secrets(secrets) -> dict:
    """Probe available platforms by validating configured API keys against model listing."""
    available: dict[str, dict] = {}

    for pid, config in get_platform_configs().items():
        key_name = config["key_name"]
        api_key = _safe_read_secret(secrets, key_name)
        if not api_key:
            continue

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


def call_llm_with_repair(
    platform: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
) -> tuple[str, bool]:
    """Call LLM and attempt JSON repair on parse failure. Returns (raw_response, was_repaired)."""
    import json

    raw_response = get_chat_response(
        platform=platform,
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    from app.corpusgen.utils import strip_markdown_fences
    try:
        json.loads(strip_markdown_fences(raw_response))
        return raw_response, False
    except Exception as exc:
        repair_prompt = _build_json_repair_prompt(raw_response, str(exc))
        repaired = get_chat_response(
            platform=platform,
            api_key=api_key,
            model=model,
            messages=[
                {"role": "system", "content": "你是一个 JSON 修复助手。你只能输出修复后的合法 JSON，不要解释。"},
                {"role": "user", "content": repair_prompt},
            ],
            temperature=0.0,
        )
        return repaired, True


def _build_json_repair_prompt(raw_response: str, error_message: str) -> str:
    return f"""下面是一段本来应该是 JSON 的模型输出，但它当前不是合法 JSON。

解析错误：
{error_message}

请你只做格式修复，不要改变原意，不要补充新的内容，不要解释。
最终只输出一个合法 JSON 对象。

原始内容：
{raw_response}
"""
