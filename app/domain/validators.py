from __future__ import annotations

from dataclasses import dataclass

from app.domain.schemas import (
    DATA_VERSION,
    OPTIONAL_EXAMPLE_FIELDS,
    REQUIRED_CONCEPT_FIELDS,
    REQUIRED_EXAMPLE_FIELDS,
)


@dataclass
class ImportValidationError(Exception):
    field: str
    reason: str
    hint: str

    def __str__(self) -> str:
        return f"{self.field}: {self.reason}（建议：{self.hint}）"


def _raise_validation(field: str, reason: str, hint: str) -> None:
    raise ImportValidationError(field=field, reason=reason, hint=hint)


def _assert_type(value, expected_type, field_name: str) -> None:
    if not isinstance(value, expected_type):
        _raise_validation(
            field=field_name,
            reason=f"类型错误，应为 `{expected_type.__name__}`",
            hint=f"将 `{field_name}` 调整为 `{expected_type.__name__}` 类型",
        )


def normalize_example(example: dict, path_prefix: str) -> dict:
    for field, expected_type in REQUIRED_EXAMPLE_FIELDS.items():
        if field not in example:
            _raise_validation(
                field=f"{path_prefix}.{field}",
                reason="缺少必需字段",
                hint=f"在该示例补充 `{field}` 字段",
            )
        _assert_type(example[field], expected_type, f"{path_prefix}.{field}")

    normalized = {
        "text": example["text"],
        "annotation": example["annotation"],
        "explanation": "",
    }

    for field, expected_type in OPTIONAL_EXAMPLE_FIELDS.items():
        if field in example and example[field] is not None:
            _assert_type(example[field], expected_type, f"{path_prefix}.{field}")
            normalized[field] = example[field]

    return normalized


def normalize_concept(concept: dict, index: int) -> dict:
    path_prefix = f"concepts[{index}]"
    for field, expected_type in REQUIRED_CONCEPT_FIELDS.items():
        if field not in concept:
            _raise_validation(
                field=f"{path_prefix}.{field}",
                reason="缺少必需字段",
                hint=f"在该概念补充 `{field}` 字段",
            )
        _assert_type(concept[field], expected_type, f"{path_prefix}.{field}")

    normalized_examples = [
        normalize_example(ex, f"{path_prefix}.examples[{example_index}]")
        for example_index, ex in enumerate(concept["examples"])
    ]

    return {
        "name": concept["name"],
        "prompt": concept["prompt"],
        "examples": normalized_examples,
        "category": concept["category"],
        "is_default": concept["is_default"],
    }


def normalize_payload(payload: dict) -> dict:
    if "concepts" not in payload:
        _raise_validation(
            field="concepts",
            reason="缺少必需字段",
            hint="在 JSON 顶层补充 `concepts` 数组",
        )

    concepts = payload["concepts"]
    if not isinstance(concepts, list):
        _raise_validation(
            field="concepts",
            reason="字段类型错误，应为 `list`",
            hint="将 `concepts` 设置为数组类型",
        )

    normalized = [normalize_concept(concept, i) for i, concept in enumerate(concepts)]
    return {
        "version": str(payload.get("version", DATA_VERSION)),
        "concepts": normalized,
    }
