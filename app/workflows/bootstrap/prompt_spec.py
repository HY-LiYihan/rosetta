from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FROZEN_PROTOCOL_PREFIXES = (
    "标签集合",
    "labels",
    "label schema",
    "输出格式",
    "output format",
    "runtime annotation format",
    "json schema",
    "json字段",
    "json 字段",
    "annotation",
    "annotation 格式",
    "annotation markup",
    "parser contract",
    "format repair",
    "frozen outputprotocolspec",
)


@dataclass(frozen=True)
class ConceptPromptSpec:
    text: str


@dataclass(frozen=True)
class FrozenOutputProtocolSpec:
    labels: tuple[str, ...]
    annotation_markup: str
    json_fields: tuple[str, ...] = ("text", "annotation", "explanation")
    max_repair_attempts: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "labels": list(self.labels),
            "json_fields": list(self.json_fields),
            "annotation_markup": self.annotation_markup,
            "parser_contract": "strict JSON parse, text equality, label validation, markup validation, span location",
            "format_repair": f"repair format only, max {self.max_repair_attempts} attempts",
        }


def strip_frozen_protocol_sections(description: str, fallback: str = "") -> str:
    """Remove labels, schemas, output formats, and repair instructions from an optimizable prompt."""
    cleaned = _strip_frozen_lines(description)
    if cleaned:
        return cleaned
    fallback_cleaned = _strip_frozen_lines(fallback)
    return fallback_cleaned or str(fallback or "").strip()


def _strip_frozen_lines(value: str) -> str:
    cleaned_lines: list[str] = []
    for line in str(value or "").splitlines():
        stripped = line.strip()
        if not stripped:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
        if _is_frozen_protocol_line(stripped):
            continue
        cleaned_lines.append(line.rstrip())
    return "\n".join(cleaned_lines).strip()


def concept_prompt_spec_from_guideline(guideline: dict[str, Any]) -> ConceptPromptSpec:
    description = strip_frozen_protocol_sections(str(guideline.get("stable_description") or ""))
    if not description:
        description = "\n".join(
            [
                f"概念定义：{str(guideline.get('brief') or '').strip()}",
                "边界规则：" + _join_rules(guideline.get("boundary_rules", []), "按最小完整语义片段标注。"),
                "排除规则：" + _join_rules(guideline.get("negative_rules", []), "不标注泛化、比喻或证据不足的片段。"),
            ]
        ).strip()
    return ConceptPromptSpec(text=description)


def frozen_output_protocol_from_guideline(guideline: dict[str, Any]) -> FrozenOutputProtocolSpec:
    labels = tuple(str(label) for label in guideline.get("labels", []) if str(label).strip()) or ("Term",)
    output_format = str(guideline.get("output_format") or "").strip() or f"[span]{{{labels[0]}}}"
    return FrozenOutputProtocolSpec(labels=labels, annotation_markup=output_format)


def ensure_concept_only_description(description: str, fallback: str = "") -> tuple[str, list[str]]:
    cleaned = strip_frozen_protocol_sections(description, fallback=fallback)
    warnings: list[str] = []
    if cleaned != str(description or "").strip():
        warnings.append("removed_frozen_output_protocol")
    return cleaned, warnings


def _is_frozen_protocol_line(line: str) -> bool:
    normalized = line.lower().lstrip("-*0123456789. 	").rstrip(":：")
    if any(normalized.startswith(prefix) for prefix in FROZEN_PROTOCOL_PREFIXES):
        return True
    protocol_markers = ("text / annotation / explanation", "text/annotation/explanation", "[span]{", "[原文]{标签}")
    return any(marker in normalized for marker in protocol_markers)


def _join_rules(value: Any, default: str) -> str:
    rules = [str(rule).strip() for rule in value or [] if str(rule).strip()]
    return "；".join(rules) or default
