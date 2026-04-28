from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.models import (
    AnnotationOption,
    AnnotationRelation,
    AnnotationSpan,
    AnnotationTask,
    Prediction,
    utc_timestamp,
)

TASK_SCHEMA_VERSION = "rosetta.prodigy_jsonl.v1"
PREDICTION_SCHEMA_VERSION = "rosetta.prodigy_prediction.v1"


def span_to_dict(span: AnnotationSpan) -> dict[str, Any]:
    payload = {
        "start": span.start,
        "end": span.end,
        "text": span.text,
        "label": span.label,
        "implicit": span.implicit,
    }
    if span.id:
        payload["id"] = span.id
    return payload


def span_from_dict(row: dict[str, Any], index: int = 1) -> AnnotationSpan:
    return AnnotationSpan(
        id=str(row.get("id") or f"T{index}"),
        start=int(row.get("start", -1)),
        end=int(row.get("end", -1)),
        text=str(row.get("text", "")),
        label=str(row.get("label", "")),
        implicit=bool(row.get("implicit", False)),
    )


def relation_to_dict(relation: AnnotationRelation) -> dict[str, Any]:
    payload: dict[str, Any] = {"label": relation.label}
    if relation.id:
        payload["id"] = relation.id
    if relation.head_span_id is not None:
        payload["head_span_id"] = relation.head_span_id
    if relation.child_span_id is not None:
        payload["child_span_id"] = relation.child_span_id
    if relation.head is not None:
        payload["head"] = relation.head
    if relation.child is not None:
        payload["child"] = relation.child
    return payload


def relation_from_dict(row: dict[str, Any], index: int = 1) -> AnnotationRelation:
    return AnnotationRelation(
        id=str(row.get("id") or f"R{index}"),
        label=str(row.get("label", "")),
        head_span_id=row.get("head_span_id"),
        child_span_id=row.get("child_span_id"),
        head=row.get("head"),
        child=row.get("child"),
    )


def option_to_dict(option: AnnotationOption) -> dict[str, str]:
    return {"id": option.id, "text": option.text}


def option_from_dict(row: dict[str, Any]) -> AnnotationOption:
    return AnnotationOption(id=str(row.get("id", "")), text=str(row.get("text", "")))


def task_to_dict(task: AnnotationTask) -> dict[str, Any]:
    task.validate()
    payload: dict[str, Any] = {
        "schema_version": TASK_SCHEMA_VERSION,
        "id": task.id,
        "text": task.text,
        "tokens": list(task.tokens),
        "spans": [span_to_dict(span) for span in task.spans],
        "relations": [relation_to_dict(relation) for relation in task.relations],
        "options": [option_to_dict(option) for option in task.options],
        "accept": list(task.accept),
        "answer": task.answer,
        "meta": dict(task.meta),
    }
    if task.label is not None:
        payload["label"] = task.label
    return payload


def task_from_dict(row: dict[str, Any]) -> AnnotationTask:
    task = AnnotationTask(
        id=str(row.get("id", "")),
        text=str(row.get("text", "")),
        tokens=tuple(row.get("tokens", [])),
        spans=tuple(span_from_dict(span, index) for index, span in enumerate(row.get("spans", []), start=1)),
        relations=tuple(
            relation_from_dict(relation, index) for index, relation in enumerate(row.get("relations", []), start=1)
        ),
        label=row.get("label"),
        options=tuple(option_from_dict(option) for option in row.get("options", [])),
        accept=tuple(row.get("accept", [])),
        answer=row.get("answer"),
        meta=dict(row.get("meta", {})),
    )
    task.validate()
    return task


def prediction_to_dict(prediction: Prediction) -> dict[str, Any]:
    prediction.validate()
    payload: dict[str, Any] = {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "id": prediction.id,
        "task_id": prediction.task_id,
        "source": prediction.source,
        "model": prediction.model,
        "spans": [span_to_dict(span) for span in prediction.spans],
        "relations": [relation_to_dict(relation) for relation in prediction.relations],
        "accept": list(prediction.accept),
        "answer": prediction.answer,
        "score": prediction.score,
        "raw_response": prediction.raw_response,
        "meta": dict(prediction.meta),
        "created_at": prediction.created_at,
    }
    if prediction.label is not None:
        payload["label"] = prediction.label
    return payload


def prediction_from_dict(row: dict[str, Any]) -> Prediction:
    prediction = Prediction(
        id=str(row.get("id", "")),
        task_id=str(row.get("task_id", "")),
        source=str(row.get("source", "model")),
        model=str(row.get("model", "")),
        spans=tuple(span_from_dict(span, index) for index, span in enumerate(row.get("spans", []), start=1)),
        relations=tuple(
            relation_from_dict(relation, index) for index, relation in enumerate(row.get("relations", []), start=1)
        ),
        label=row.get("label"),
        accept=tuple(row.get("accept", [])),
        answer=row.get("answer"),
        score=row.get("score"),
        raw_response=str(row.get("raw_response", "")),
        meta=dict(row.get("meta", {})),
        created_at=str(row.get("created_at", "")) or utc_timestamp(),
    )
    prediction.validate()
    return prediction


def read_tasks_jsonl(path: str | Path) -> list[AnnotationTask]:
    tasks: list[AnnotationTask] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        tasks.append(task_from_dict(json.loads(line)))
    return tasks


def write_tasks_jsonl(path: str | Path, tasks: list[AnnotationTask]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for task in tasks:
            handle.write(json.dumps(task_to_dict(task), ensure_ascii=False) + "\n")
