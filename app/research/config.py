from __future__ import annotations

import json
from pathlib import Path

from app.domain.annotation_format import validate_annotation_markup
from app.research.contracts import ConflictRule, ResearchConfig, ResearchExample

DEFAULT_OUTPUT_CONTRACT = ("text", "annotation", "explanation")
DEFAULT_SYSTEM_PROMPT = "你是一个严谨的语言学科研标注助手，必须严格遵守任务定义、负向约束与 JSON 输出要求。"


class ResearchConfigError(ValueError):
    """Raised when a research pipeline config is invalid."""


def _require_str(payload: dict, field: str, source: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ResearchConfigError(f"{source}: `{field}` 必须是非空字符串")
    return value.strip()


def _read_str_list(payload: dict, field: str, source: str) -> tuple[str, ...]:
    value = payload.get(field, [])
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ResearchConfigError(f"{source}: `{field}` 必须是字符串列表")
    return tuple(item.strip() for item in value)


def _parse_example(payload: dict, field: str, index: int) -> ResearchExample:
    source = f"{field}[{index}]"
    if not isinstance(payload, dict):
        raise ResearchConfigError(f"{source}: 示例必须是对象")

    annotation = _require_str(payload, "annotation", source)
    ok, reason = validate_annotation_markup(annotation)
    if not ok:
        raise ResearchConfigError(f"{source}: annotation 不合法: {reason}")

    example_type = payload.get("example_type")
    if example_type is None:
        example_type = "hard" if field == "hard_examples" else "canonical"
    if example_type not in {"canonical", "hard"}:
        raise ResearchConfigError(f"{source}: `example_type` 只能是 `canonical` 或 `hard`")

    return ResearchExample(
        id=_require_str(payload, "id", source),
        text=_require_str(payload, "text", source),
        annotation=annotation,
        explanation=_require_str(payload, "explanation", source),
        rationale=str(payload.get("rationale", "")).strip(),
        example_type=example_type,
    )


def _parse_conflict_rule(payload: dict, index: int) -> ConflictRule:
    source = f"conflict_rules[{index}]"
    if not isinstance(payload, dict):
        raise ResearchConfigError(f"{source}: 冲突规则必须是对象")

    labels = payload.get("labels", [])
    if not isinstance(labels, list) or len(labels) < 2 or any(not isinstance(item, str) or not item.strip() for item in labels):
        raise ResearchConfigError(f"{source}: `labels` 必须至少包含 2 个非空标签")

    return ConflictRule(
        name=_require_str(payload, "name", source),
        labels=tuple(item.strip() for item in labels),
        message=_require_str(payload, "message", source),
    )


def parse_research_config(payload: dict, source: str = "<memory>") -> ResearchConfig:
    if not isinstance(payload, dict):
        raise ResearchConfigError(f"{source}: 顶层必须是 JSON 对象")

    canonical_examples = tuple(
        _parse_example(example, "canonical_examples", index)
        for index, example in enumerate(payload.get("canonical_examples", []))
    )
    hard_examples = tuple(
        _parse_example(example, "hard_examples", index)
        for index, example in enumerate(payload.get("hard_examples", []))
    )

    if not canonical_examples and not hard_examples:
        raise ResearchConfigError(f"{source}: 至少需要一个 canonical 或 hard 示例")

    output_contract = tuple(payload.get("output_contract", list(DEFAULT_OUTPUT_CONTRACT)))
    if not output_contract or any(not isinstance(item, str) or not item.strip() for item in output_contract):
        raise ResearchConfigError(f"{source}: `output_contract` 必须是非空字段列表")
    required_fields = set(DEFAULT_OUTPUT_CONTRACT)
    if not required_fields.issubset(set(output_contract)):
        raise ResearchConfigError(f"{source}: `output_contract` 至少要包含 {DEFAULT_OUTPUT_CONTRACT}")

    retrieval_strategy = str(payload.get("retrieval_strategy", "lexical")).strip().lower()
    if retrieval_strategy not in {"lexical"}:
        raise ResearchConfigError(f"{source}: 当前仅支持 `lexical` 检索策略")

    temperature = float(payload.get("temperature", 0.0))
    top_k_examples = int(payload.get("top_k_examples", 3))
    if top_k_examples < 1:
        raise ResearchConfigError(f"{source}: `top_k_examples` 必须 >= 1")

    return ResearchConfig(
        name=_require_str(payload, "name", source),
        description=str(payload.get("description", "")).strip(),
        platform=_require_str(payload, "platform", source),
        model=_require_str(payload, "model", source),
        api_key_env=_require_str(payload, "api_key_env", source),
        system_prompt=str(payload.get("system_prompt", DEFAULT_SYSTEM_PROMPT)).strip() or DEFAULT_SYSTEM_PROMPT,
        definition=_require_str(payload, "definition", source),
        inclusion_rules=_read_str_list(payload, "inclusion_rules", source),
        exclusion_rules=_read_str_list(payload, "exclusion_rules", source),
        negative_constraints=_read_str_list(payload, "negative_constraints", source),
        output_contract=tuple(item.strip() for item in output_contract),
        temperature=temperature,
        top_k_examples=top_k_examples,
        retrieval_strategy=retrieval_strategy,
        output_dir=str(payload.get("output_dir", ".runtime/research")).strip() or ".runtime/research",
        canonical_examples=canonical_examples,
        hard_examples=hard_examples,
        conflict_rules=tuple(
            _parse_conflict_rule(rule, index)
            for index, rule in enumerate(payload.get("conflict_rules", []))
        ),
    )


def load_research_config(path: str | Path) -> ResearchConfig:
    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    return parse_research_config(payload, source=str(config_path))
