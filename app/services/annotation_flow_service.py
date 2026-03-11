from __future__ import annotations

from app.services.annotation_service import (
    build_annotation_prompt,
    build_history_entry,
    parse_annotation_response,
)
from app.services.platform_service import get_chat_response


def run_annotation(
    concept: dict,
    input_text: str,
    available_config: dict,
    selected_platform: str | None,
    selected_model: str | None,
    temperature: float,
) -> dict:
    """Execute end-to-end annotation flow and return structured result."""
    if not selected_platform:
        return {"ok": False, "error": "没有可用的 AI 平台，请检查 secrets.toml 配置"}

    platform_config = available_config.get(selected_platform, {})
    api_key = platform_config.get("api_key")
    if not api_key:
        return {"ok": False, "error": f"平台 {selected_platform} 缺少 API Key"}

    prompt = build_annotation_prompt(concept, input_text)
    raw_result = get_chat_response(
        platform=selected_platform,
        api_key=api_key,
        model=selected_model,
        messages=[
            {"role": "system", "content": "你是一个专业的语言学助手，擅长文本标注和分析。"},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    parsed_result, parse_warning = parse_annotation_response(raw_result)

    history_entry = build_history_entry(
        concept_name=concept["name"],
        input_text=input_text,
        annotation_result=raw_result,
        parsed_result=parsed_result,
        platform=selected_platform,
        model=selected_model,
        temperature=temperature,
    )
    return {
        "ok": True,
        "raw_result": raw_result,
        "parsed_result": parsed_result,
        "parse_warning": parse_warning,
        "history_entry": history_entry,
    }
