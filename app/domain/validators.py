from __future__ import annotations

from dataclasses import dataclass

from app.domain.annotation_doc import make_annotation_doc, validate_annotation_doc
from app.domain.annotation_format import validate_annotation_markup
from app.domain.schemas import (
    DATA_VERSION,
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
        if field != "annotation":
            _assert_type(example[field], expected_type, f"{path_prefix}.{field}")

    annotation = example["annotation"]
    if isinstance(annotation, str):
        ok, reason = validate_annotation_markup(annotation)
        if not ok:
            _raise_validation(
                field=f"{path_prefix}.annotation",
                reason=f"标注格式不合法: {reason}",
                hint="使用 [原文]{概念标签}；隐含义使用 [!隐含义]{概念标签}",
            )
        annotation = make_annotation_doc(example["text"], annotation)
    elif isinstance(annotation, dict):
        ok, reason = validate_annotation_doc(annotation)
        if not ok:
            _raise_validation(
                field=f"{path_prefix}.annotation",
                reason=f"AnnotationDoc 格式不合法: {reason}",
                hint="annotation 必须为合法的 AnnotationDoc dict",
            )
    else:
        _raise_validation(
            field=f"{path_prefix}.annotation",
            reason="类型错误，必须为 str 或 dict",
            hint="使用 [原文]{概念标签} 字符串，或合法的 AnnotationDoc dict",
        )

    if not example["explanation"].strip():
        _raise_validation(
            field=f"{path_prefix}.explanation",
            reason="解释不能为空",
            hint="每个示例必须提供 explanation，用于说明标注依据",
        )

    return {
        "text": example["text"],
        "annotation": annotation,
        "explanation": example["explanation"],
    }


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
