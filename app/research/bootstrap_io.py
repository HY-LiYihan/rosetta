from __future__ import annotations

import json
from pathlib import Path

from app.domain.annotation_doc import legacy_string_to_spans, spans_to_legacy_string
from app.research.bootstrap_contracts import (
    BootstrapCandidate,
    BootstrapDataError,
    BootstrapSample,
    BootstrapSpan,
    normalize_confidence,
    validate_span_against_text,
)


def span_from_dict(payload: dict, source_text: str) -> BootstrapSpan:
    if not isinstance(payload, dict):
        raise BootstrapDataError("span 必须是 JSON 对象")

    implicit = bool(payload.get("implicit", False))
    span = BootstrapSpan(
        start=int(payload.get("start", payload.get("begin", -1 if implicit else 0))),
        end=int(payload.get("end", -1 if implicit else 0)),
        text=str(payload.get("text", "")).strip(),
        label=str(payload.get("label", "")).strip(),
        implicit=implicit,
    )
    validate_span_against_text(span, source_text)
    return span


def span_to_dict(span: BootstrapSpan) -> dict:
    return {
        "start": span.start,
        "end": span.end,
        "text": span.text,
        "label": span.label,
        "implicit": span.implicit,
    }


def span_to_prodigy_dict(span: BootstrapSpan, index: int) -> dict:
    row = {"id": f"T{index + 1}"}
    row.update(span_to_dict(span))
    return row


def spans_from_markup(source_text: str, annotation_markup: str) -> tuple[BootstrapSpan, ...]:
    spans = []
    for row in legacy_string_to_spans(source_text, annotation_markup):
        span = BootstrapSpan(
            start=int(row["start"]),
            end=int(row["end"]),
            text=str(row["text"]),
            label=str(row["label"]),
            implicit=bool(row.get("implicit", False)),
        )
        validate_span_against_text(span, source_text)
        spans.append(span)
    return tuple(spans)


def sample_from_dict(payload: dict, index: int = 1) -> BootstrapSample:
    if not isinstance(payload, dict):
        raise BootstrapDataError(f"line {index}: 样本必须是 JSON 对象")

    text = str(payload.get("text", "")).strip()
    if not text:
        raise BootstrapDataError(f"line {index}: text 不能为空")

    sample_id = str(payload.get("id") or f"sample-{index:04d}").strip()
    metadata = payload.get("meta") or payload.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise BootstrapDataError(f"line {index}: metadata 必须是对象")

    raw_spans = payload.get("spans")
    if raw_spans is None and isinstance(payload.get("gold_annotation"), str):
        spans = spans_from_markup(text, payload["gold_annotation"])
    elif raw_spans is None and isinstance(payload.get("annotation"), dict):
        raw_spans = payload["annotation"].get("layers", {}).get("spans")
        spans = _spans_from_list(raw_spans, text, index)
    else:
        spans = _spans_from_list(raw_spans or [], text, index)

    return BootstrapSample(id=sample_id, text=text, spans=spans, metadata=dict(metadata))


def sample_to_dict(sample: BootstrapSample) -> dict:
    return {
        "schema_version": "rosetta.prodigy_jsonl.v1",
        "id": sample.id,
        "text": sample.text,
        "tokens": [],
        "spans": [span_to_prodigy_dict(span, index) for index, span in enumerate(sample.spans)],
        "relations": [],
        "answer": "accept",
        "meta": sample.metadata,
    }


def candidate_from_dict(payload: dict, index: int = 1) -> BootstrapCandidate:
    if not isinstance(payload, dict):
        raise BootstrapDataError(f"line {index}: candidate 必须是 JSON 对象")

    sample_id = str(payload.get("sample_id", "")).strip()
    if not sample_id:
        raise BootstrapDataError(f"line {index}: sample_id 不能为空")

    source_text = str(payload.get("text", payload.get("source_text", ""))).strip()
    runtime_annotation = payload.get("runtime_annotation") or {}
    runtime_markup = runtime_annotation.get("annotation_markup") if isinstance(runtime_annotation, dict) else None
    annotation_markup = str(payload.get("annotation_markup", runtime_markup or payload.get("annotation_markup_legacy", ""))).strip()
    if not annotation_markup and isinstance(payload.get("annotation"), str):
        annotation_markup = str(payload["annotation"]).strip()
    raw_spans = payload.get("spans")
    if raw_spans is None and isinstance(payload.get("annotation"), dict):
        raw_spans = payload["annotation"].get("layers", {}).get("spans")

    if raw_spans is None and annotation_markup and source_text:
        spans = spans_from_markup(source_text, annotation_markup)
    elif raw_spans is not None and source_text:
        spans = _spans_from_list(raw_spans, source_text, index)
    else:
        spans = tuple()

    if not annotation_markup and spans:
        annotation_markup = spans_to_legacy_string([span_to_dict(span) for span in spans])

    return BootstrapCandidate(
        sample_id=sample_id,
        candidate_id=str(payload.get("candidate_id") or payload.get("run_id") or f"candidate-{index:03d}").strip(),
        annotation_markup=annotation_markup,
        spans=spans,
        text=source_text,
        explanation=str(payload.get("explanation", "")).strip(),
        model_confidence=normalize_confidence(payload.get("model_confidence")),
        uncertainty_reason=str(payload.get("uncertainty_reason", "")).strip(),
        raw_response=str(payload.get("raw_response", "")),
        metadata=dict(payload.get("meta") or payload.get("metadata") or {}),
    )


def candidate_to_dict(candidate: BootstrapCandidate) -> dict:
    row = {
        "schema_version": "rosetta.prodigy_candidate.v1",
        "sample_id": candidate.sample_id,
        "candidate_id": candidate.candidate_id,
        "text": candidate.text,
        "tokens": [],
        "spans": [span_to_prodigy_dict(span, index) for index, span in enumerate(candidate.spans)],
        "relations": [],
        "answer": None,
        "runtime_annotation": {
            "format": "inline_markup.v1",
            "annotation_markup": candidate.annotation_markup,
        },
        "explanation": candidate.explanation,
        "model_confidence": candidate.model_confidence,
        "uncertainty_reason": candidate.uncertainty_reason,
        "raw_response": candidate.raw_response,
        "meta": candidate.metadata,
    }
    return row


def read_samples_jsonl(path: str | Path) -> list[BootstrapSample]:
    return [sample_from_dict(row, index) for index, row in enumerate(_read_jsonl(Path(path)), start=1)]


def write_samples_jsonl(path: str | Path, samples: list[BootstrapSample]) -> None:
    _write_jsonl(Path(path), [sample_to_dict(sample) for sample in samples])


def read_candidates_jsonl(path: str | Path) -> list[BootstrapCandidate]:
    return [candidate_from_dict(row, index) for index, row in enumerate(_read_jsonl(Path(path)), start=1)]


def write_candidates_jsonl(path: str | Path, candidates: list[BootstrapCandidate]) -> None:
    _write_jsonl(Path(path), [candidate_to_dict(candidate) for candidate in candidates])


def _spans_from_list(value: object, source_text: str, index: int) -> tuple[BootstrapSpan, ...]:
    if not isinstance(value, list):
        raise BootstrapDataError(f"line {index}: spans 必须是列表")
    return tuple(span_from_dict(row, source_text) for row in value)


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BootstrapDataError(f"{path}:{line_number}: JSON 解析失败: {exc}") from exc
        rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
