from __future__ import annotations

from app.domain.schemas import (
    DATA_VERSION,
    OPTIONAL_EXAMPLE_FIELDS,
    REQUIRED_CONCEPT_FIELDS,
    REQUIRED_EXAMPLE_FIELDS,
)


def _assert_type(value, expected_type, field_name: str) -> None:
    if not isinstance(value, expected_type):
        raise ValueError(f"字段 `{field_name}` 类型错误，应为 {expected_type.__name__}")


def normalize_example(example: dict) -> dict:
    for field, expected_type in REQUIRED_EXAMPLE_FIELDS.items():
        if field not in example:
            raise ValueError(f"示例缺少必需字段 `{field}`")
        _assert_type(example[field], expected_type, field)

    normalized = {
        "text": example["text"],
        "annotation": example["annotation"],
        "explanation": "",
    }

    for field, expected_type in OPTIONAL_EXAMPLE_FIELDS.items():
        if field in example and example[field] is not None:
            _assert_type(example[field], expected_type, field)
            normalized[field] = example[field]

    return normalized


def normalize_concept(concept: dict) -> dict:
    for field, expected_type in REQUIRED_CONCEPT_FIELDS.items():
        if field not in concept:
            raise ValueError(f"概念缺少必需字段 `{field}`")
        _assert_type(concept[field], expected_type, field)

    normalized_examples = [normalize_example(ex) for ex in concept["examples"]]

    return {
        "name": concept["name"],
        "prompt": concept["prompt"],
        "examples": normalized_examples,
        "category": concept["category"],
        "is_default": concept["is_default"],
    }


def normalize_payload(payload: dict) -> dict:
    if "concepts" not in payload:
        raise ValueError("文件格式错误：缺少 `concepts` 字段")

    concepts = payload["concepts"]
    if not isinstance(concepts, list):
        raise ValueError("文件格式错误：`concepts` 必须是数组")

    normalized = [normalize_concept(concept) for concept in concepts]
    return {
        "version": str(payload.get("version", DATA_VERSION)),
        "concepts": normalized,
    }
