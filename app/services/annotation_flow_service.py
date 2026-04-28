from __future__ import annotations

from app.infrastructure.debug import log_debug_event
from app.services.platform_service import get_chat_response
from app.workflows.annotation import run_agentic_annotation


def run_annotation(
    concept: dict,
    input_text: str,
    available_config: dict,
    selected_platform: str | None,
    selected_model: str | None,
    temperature: float,
) -> dict:
    """Execute end-to-end annotation flow and return structured result."""
    log_debug_event(
        "annotation_requested",
        {
            "concept": concept.get("name"),
            "text": input_text,
            "platform": selected_platform,
            "model": selected_model,
            "temperature": temperature,
        },
    )
    if not selected_platform:
        return {"ok": False, "error": "没有可用的 AI 平台，请检查 secrets.toml 配置"}

    platform_config = available_config.get(selected_platform, {})
    api_key = platform_config.get("api_key")
    if not api_key:
        return {"ok": False, "error": f"平台 {selected_platform} 缺少 API Key"}

    def predictor(system_prompt: str, messages: list[dict], call_temperature: float) -> str:
        return get_chat_response(
            platform=selected_platform,
            api_key=api_key,
            model=selected_model,
            messages=[{"role": "system", "content": system_prompt}, *messages],
            temperature=call_temperature,
        )

    result = run_agentic_annotation(
        concept=concept,
        input_text=input_text,
        predictor=predictor,
        platform=selected_platform,
        model=selected_model,
        temperature=temperature,
    )
    prompt = result.get("agent_result").state.get("prompt") if result.get("ok") else ""
    log_debug_event("annotation_prompt_built", {"prompt": prompt})
    log_debug_event(
        "annotation_response_received",
        {
            "raw_result": result.get("raw_result"),
            "parsed_result": result.get("parsed_result"),
            "parse_warning": result.get("parse_warning"),
            "agent_ok": result.get("ok"),
        },
    )
    return result
