from __future__ import annotations

from dataclasses import dataclass, field


class BootstrapDataError(ValueError):
    """Raised when bootstrap JSONL data is invalid."""


@dataclass(frozen=True)
class BootstrapSpan:
    start: int
    end: int
    text: str
    label: str
    implicit: bool = False


@dataclass(frozen=True)
class BootstrapSample:
    id: str
    text: str
    spans: tuple[BootstrapSpan, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class BootstrapCandidate:
    sample_id: str
    candidate_id: str
    annotation_markup: str
    spans: tuple[BootstrapSpan, ...]
    explanation: str = ""
    model_confidence: float | None = None
    uncertainty_reason: str = ""
    raw_response: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


def validate_span_against_text(span: BootstrapSpan, source_text: str) -> None:
    if not span.text.strip():
        raise BootstrapDataError("span.text 不能为空")
    if not span.label.strip():
        raise BootstrapDataError(f"span `{span.text}` 的 label 不能为空")

    if span.implicit:
        if span.start != -1 or span.end != -1:
            raise BootstrapDataError(f"隐含 span `{span.text}` 的 start/end 必须为 -1")
        return

    if span.start < 0 or span.end <= span.start:
        raise BootstrapDataError(f"span `{span.text}` 的 start/end 非法")
    if span.end > len(source_text):
        raise BootstrapDataError(f"span `{span.text}` 的 end 超出原文长度")
    if source_text[span.start : span.end] != span.text:
        raise BootstrapDataError(
            f"span offset 与原文不一致: expected `{span.text}`, actual `{source_text[span.start:span.end]}`"
        )


def normalize_confidence(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise BootstrapDataError(f"model_confidence 必须是 0-1 数值: {value}") from exc
    if confidence < 0 or confidence > 1:
        raise BootstrapDataError(f"model_confidence 必须位于 0-1: {confidence}")
    return round(confidence, 4)
