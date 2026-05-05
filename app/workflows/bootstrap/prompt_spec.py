from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SPAN_MARKUP_PROTOCOL = "span_markup"
FULL_JSON_PROTOCOL = "full_json"
FULL_JSON_OUTPUT_FORMAT = "rosetta.annotation_doc.v3.1.full_json"
DEFAULT_SPAN_LABEL = "Term"


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
    protocol: str = SPAN_MARKUP_PROTOCOL
    json_fields: tuple[str, ...] = ("text", "annotation", "explanation")
    max_repair_attempts: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
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
            ]
        ).strip()
    return ConceptPromptSpec(text=description)


def frozen_output_protocol_from_guideline(guideline: dict[str, Any]) -> FrozenOutputProtocolSpec:
    labels = tuple(str(label) for label in guideline.get("labels", []) if str(label).strip()) or (DEFAULT_SPAN_LABEL,)
    output_format = str(guideline.get("output_format") or "").strip()
    if is_full_json_output_format(output_format):
        return FrozenOutputProtocolSpec(
            labels=labels,
            protocol=FULL_JSON_PROTOCOL,
            annotation_markup="完整 AnnotationDoc JSON（spans / relations / attributes / comments / document_labels）",
        )
    return FrozenOutputProtocolSpec(
        labels=labels,
        protocol=SPAN_MARKUP_PROTOCOL,
        annotation_markup=output_format or span_markup_output_format(labels[0]),
    )


def span_markup_output_format(label: str = DEFAULT_SPAN_LABEL) -> str:
    return f"[span]{{{str(label or DEFAULT_SPAN_LABEL).strip() or DEFAULT_SPAN_LABEL}}}"


def is_full_json_output_format(output_format: str) -> bool:
    normalized = str(output_format or "").strip().lower()
    return normalized in {FULL_JSON_OUTPUT_FORMAT, FULL_JSON_PROTOCOL, "annotationdoc", "annotation_doc", "full annotationdoc json"}


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
