from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PromptSegment:
    id: str
    kind: str
    text: str
    index: int
    mutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "text": self.text,
            "index": self.index,
            "mutable": self.mutable,
        }


@dataclass(frozen=True)
class TextGradient:
    segment_id: str
    method: str
    direction: str
    score: float
    evidence: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "method": self.method,
            "direction": self.direction,
            "score": round(float(self.score), 4),
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class PromptOptimizationTrace:
    segment_id: str
    perturbation_method: str
    gradient_direction: str
    current_loss: float
    candidate_loss: float | None = None
    loss_delta: float | None = None
    length_delta: int = 0
    accepted: bool = False
    diagnostics: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "perturbation_method": self.perturbation_method,
            "gradient_direction": self.gradient_direction,
            "current_loss": round(float(self.current_loss), 4),
            "candidate_loss": None if self.candidate_loss is None else round(float(self.candidate_loss), 4),
            "loss_delta": None if self.loss_delta is None else round(float(self.loss_delta), 4),
            "length_delta": self.length_delta,
            "accepted": self.accepted,
            "diagnostics": self.diagnostics,
            "metadata": self.metadata,
        }


HEADING_KINDS = (
    ("概念描述", "task_definition"),
    ("Concept description", "task_definition"),
    ("Concept Description", "task_definition"),
    ("标签集合", "label_schema"),
    ("Labels", "label_schema"),
    ("Label schema", "label_schema"),
    ("边界规则", "boundary_rules"),
    ("Boundary rules", "boundary_rules"),
    ("排除规则", "negative_rules"),
    ("负例规则", "negative_rules"),
    ("Negative rules", "negative_rules"),
    ("输出格式", "output_format"),
    ("Output format", "output_format"),
    ("边界补充", "boundary_rules"),
    ("Boundary supplement", "boundary_rules"),
)


def segment_prompt(description: str) -> list[PromptSegment]:
    lines = [line.rstrip() for line in str(description or "").splitlines()]
    segments: list[PromptSegment] = []
    pending: list[str] = []
    pending_kind = "task_definition"

    def flush() -> None:
        nonlocal pending, pending_kind
        text = "\n".join(line for line in pending if line.strip()).strip()
        if not text:
            pending = []
            return
        index = len(segments) + 1
        segments.append(
            PromptSegment(
                id=f"seg-{index:02d}-{pending_kind}",
                kind=pending_kind,
                text=text,
                index=index,
                mutable=pending_kind not in {"output_format", "label_schema"},
            )
        )
        pending = []

    for line in lines:
        if not line.strip():
            flush()
            continue
        kind = _line_kind(line)
        if kind is not None:
            flush()
            pending_kind = kind
        pending.append(line)
    flush()
    if not segments and str(description or "").strip():
        return [
            PromptSegment(
                id="seg-01-task_definition",
                kind="task_definition",
                text=str(description).strip(),
                index=1,
            )
        ]
    return segments


def estimate_text_gradients(
    description: str,
    validation_result: dict,
    failure_summary: str,
    current_loss: dict | None = None,
) -> list[TextGradient]:
    segments = segment_prompt(description)
    if not segments:
        return []
    details = validation_result.get("details", [])
    missing_count = sum(len(detail.get("missing_spans", [])) for detail in details)
    extra_count = sum(len(detail.get("extra_spans", [])) for detail in details)
    failed_count = len(validation_result.get("failed", []))
    unstable_count = len(validation_result.get("unstable", []))
    loss_value = float((current_loss or {}).get("loss", 0.0))
    gradients: list[TextGradient] = []
    for segment in segments:
        if not segment.mutable:
            continue
        score = _segment_score(segment.kind, missing_count, extra_count, failed_count, unstable_count, loss_value)
        direction = _segment_direction(segment.kind, missing_count, extra_count)
        if score <= 0:
            continue
        gradients.append(
            TextGradient(
                segment_id=segment.id,
                method="mask_ablation",
                direction=direction,
                score=score,
                evidence=_gradient_evidence(segment.kind, missing_count, extra_count, failed_count, unstable_count),
                metadata={
                    "failure_summary": failure_summary,
                    "missing_count": missing_count,
                    "extra_count": extra_count,
                    "failed_count": failed_count,
                    "unstable_count": unstable_count,
                },
            )
        )
    gradients.sort(key=lambda gradient: gradient.score, reverse=True)
    return gradients


def build_llm_adamw_trace(
    description: str,
    validation_result: dict,
    failure_summary: str,
    current_loss: dict,
) -> dict[str, Any]:
    segments = segment_prompt(description)
    gradients = estimate_text_gradients(description, validation_result, failure_summary, current_loss)
    top_gradient = gradients[0] if gradients else None
    trace = PromptOptimizationTrace(
        segment_id=top_gradient.segment_id if top_gradient else "",
        perturbation_method=top_gradient.method if top_gradient else "none",
        gradient_direction=top_gradient.direction if top_gradient else "no_gradient",
        current_loss=float(current_loss.get("loss", 0.0)),
        diagnostics=top_gradient.evidence if top_gradient else "没有检测到可用文本梯度。",
        metadata={"optimizer": "llm_adamw", "length_decay": True},
    )
    return {
        "optimizer": "llm_adamw",
        "segments": [segment.to_dict() for segment in segments],
        "text_gradients": [gradient.to_dict() for gradient in gradients],
        "proposed_trace": trace.to_dict(),
        "top_segment_id": top_gradient.segment_id if top_gradient else "",
        "top_direction": top_gradient.direction if top_gradient else "no_gradient",
    }


def finalize_candidate_trace(
    base_trace: dict[str, Any],
    candidate_id: str,
    current_description: str,
    candidate_description: str,
    current_loss: dict,
    candidate_loss: dict,
    accepted: bool,
) -> dict[str, Any]:
    proposed = dict(base_trace.get("proposed_trace", {}))
    current_loss_value = float(current_loss.get("loss", 0.0))
    candidate_loss_value = float(candidate_loss.get("loss", current_loss_value))
    proposed.update(
        {
            "candidate_id": candidate_id,
            "candidate_loss": round(candidate_loss_value, 4),
            "loss_delta": round(current_loss_value - candidate_loss_value, 4),
            "length_delta": len(candidate_description) - len(current_description),
            "accepted": accepted,
        }
    )
    return {
        "optimizer": base_trace.get("optimizer", "llm_adamw"),
        "candidate_id": candidate_id,
        "segments": base_trace.get("segments", []),
        "text_gradients": base_trace.get("text_gradients", []),
        "trace": proposed,
    }


def length_penalized_loss(candidate_loss: dict, current_description: str, candidate_description: str) -> dict:
    raw_loss = float(candidate_loss.get("loss", 0.0))
    length_delta = max(0, len(candidate_description) - len(current_description))
    penalty = round(length_delta / 500.0, 4)
    updated = dict(candidate_loss)
    updated["raw_loss"] = round(raw_loss, 4)
    updated["length_penalty"] = penalty
    updated["length_delta"] = len(candidate_description) - len(current_description)
    updated["loss"] = round(raw_loss + penalty, 4)
    return updated


def _line_kind(line: str) -> str | None:
    normalized = line.strip().rstrip(":：").lower()
    for prefix, kind in HEADING_KINDS:
        if normalized.startswith(prefix.lower()):
            return kind
    return None


def _segment_score(
    kind: str,
    missing_count: int,
    extra_count: int,
    failed_count: int,
    unstable_count: int,
    loss_value: float,
) -> float:
    base = failed_count + unstable_count * 0.5 + loss_value * 0.05
    if kind == "boundary_rules":
        return base + missing_count * 1.2 + extra_count * 1.0
    if kind == "negative_rules":
        return base * 0.7 + extra_count * 1.5
    if kind == "task_definition":
        return base * 0.8 + missing_count * 1.0
    return base * 0.4


def _segment_direction(kind: str, missing_count: int, extra_count: int) -> str:
    if kind == "negative_rules":
        return "tighten_exclusions" if extra_count >= missing_count else "keep_exclusions"
    if kind == "boundary_rules":
        if missing_count > extra_count:
            return "expand_recall_boundary"
        if extra_count > missing_count:
            return "tighten_boundary"
        return "stabilize_boundary"
    if kind == "task_definition":
        return "clarify_task_scope"
    return "minimal_revision"


def _gradient_evidence(
    kind: str,
    missing_count: int,
    extra_count: int,
    failed_count: int,
    unstable_count: int,
) -> str:
    if kind == "negative_rules" and extra_count:
        return f"检测到 {extra_count} 个多标片段，优先收紧排除规则。"
    if kind == "boundary_rules":
        return f"检测到 {missing_count} 个漏标片段、{extra_count} 个多标片段，边界规则影响最大。"
    if kind == "task_definition":
        return f"检测到 {failed_count} 个失败样例、{unstable_count} 个不稳定样例，需要澄清任务范围。"
    return "该片段可能影响当前 gold loss。"
