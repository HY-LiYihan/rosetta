from __future__ import annotations

from typing import Callable

from app.agents.kernel import AgentKernel, AgentPolicy
from app.agents.tools import Tool, ToolRegistry
from app.services.annotation_service import (
    build_annotation_prompt,
    build_history_entry,
    parse_annotation_response,
)

Predictor = Callable[[str, list[dict], float], str]


def run_agentic_annotation(
    concept: dict,
    input_text: str,
    predictor: Predictor,
    platform: str,
    model: str | None,
    temperature: float,
    kernel: AgentKernel | None = None,
) -> dict:
    prompt = build_annotation_prompt(concept, input_text)

    def call_model(invocation):
        raw_result = predictor(
            "你是一个专业的语言学助手，擅长文本标注和分析。",
            [{"role": "user", "content": prompt}],
            temperature,
        )
        parsed_result, parse_warning = parse_annotation_response(raw_result)
        history_entry = build_history_entry(
            concept_name=concept["name"],
            input_text=input_text,
            annotation_result=raw_result,
            parsed_result=parsed_result,
            platform=platform,
            model=model,
            temperature=temperature,
        )
        return {
            "prompt": prompt,
            "raw_result": raw_result,
            "parsed_result": parsed_result,
            "parse_warning": parse_warning,
            "history_entry": history_entry,
        }

    registry = ToolRegistry(
        [
            Tool(
                name="annotate_text",
                description="Build prompt, call the selected LLM, parse the annotation response.",
                handler=call_model,
            )
        ]
    )
    result = (kernel or AgentKernel()).run(
        goal=f"Annotate text with concept `{concept.get('name', '')}`",
        context={"concept": concept, "input_text": input_text},
        tools=registry,
        policy=AgentPolicy(model=model or "", temperature=temperature),
        tool_plan=["annotate_text"],
        workflow="annotation",
    )
    if not result.ok:
        return {"ok": False, "error": result.error, "agent_result": result}
    return {
        "ok": True,
        "raw_result": result.state["raw_result"],
        "parsed_result": result.state["parsed_result"],
        "parse_warning": result.state["parse_warning"],
        "history_entry": result.state["history_entry"],
        "agent_result": result,
    }
