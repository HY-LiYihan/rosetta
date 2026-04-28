from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.core.models import AnnotationOption, AnnotationSpan, AnnotationTask, Prediction, ReviewTask
from app.data.prodigy_jsonl import prediction_from_dict, task_from_dict
from app.runtime.store import RuntimeStore


def list_review_queue(
    store: RuntimeStore,
    threshold: float = 0.75,
    include_audit: bool = True,
    job_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    reviews = store.list_reviews(limit=5000, status="pending")
    queue: list[dict[str, Any]] = []
    for row in reviews:
        payload = row["payload"]
        meta = payload.get("meta", {})
        score = float(meta.get("score", 0.0))
        is_audit = meta.get("route_reason") == "高置信抽检"
        if job_id and meta.get("job_id") != job_id:
            continue
        if score <= threshold or (include_audit and is_audit):
            queue.append(row)

    queue.sort(
        key=lambda row: (
            float(row["payload"].get("meta", {}).get("score", 0.0)),
            float(row["payload"].get("meta", {}).get("agreement", 0.0)),
            float(row["payload"].get("meta", {}).get("avg_confidence", 0.0)),
            row["created_at"],
        )
    )
    return queue[:limit]


def get_next_review_task(
    store: RuntimeStore,
    threshold: float = 0.75,
    include_audit: bool = True,
    job_id: str | None = None,
) -> dict[str, Any] | None:
    queue = list_review_queue(store, threshold=threshold, include_audit=include_audit, job_id=job_id, limit=1)
    if not queue:
        return None

    review_payload = queue[0]["payload"]
    task_row = store.get_task(review_payload["task_id"])
    if task_row is None:
        return {"review": review_payload, "task": None, "predictions": [], "guideline": None, "gold_examples": []}

    predictions = []
    for prediction_id in review_payload.get("prediction_ids", []):
        prediction_row = store.get_prediction(prediction_id)
        if prediction_row is not None:
            predictions.append(prediction_row["payload"])

    guideline = None
    gold_examples: list[dict[str, Any]] = []
    job_id_from_review = review_payload.get("meta", {}).get("job_id")
    if job_id_from_review:
        job_row = store.get_job(job_id_from_review)
        if job_row is not None:
            guideline_row = store.get_guideline(job_row["payload"]["guideline_id"])
            guideline = guideline_row["payload"] if guideline_row else None
            gold_sets = store.list_gold_example_sets(guideline_id=job_row["payload"]["guideline_id"], limit=1)
            if gold_sets:
                for task_id in gold_sets[0]["payload"].get("task_ids", [])[:3]:
                    gold_row = store.get_task(task_id)
                    if gold_row is not None:
                        gold_examples.append(gold_row["payload"])

    return {
        "review": review_payload,
        "task": task_row["payload"],
        "predictions": predictions,
        "guideline": guideline,
        "gold_examples": gold_examples,
    }


def apply_review_decision(
    store: RuntimeStore,
    review_id: str,
    decision: str,
    selected_option_id: str | None = None,
    manual_spans: list[dict[str, Any]] | None = None,
    note: str = "",
    hard_example: bool = False,
) -> dict[str, Any]:
    review_row = store.get_review(review_id)
    if review_row is None:
        raise ValueError(f"未找到审核任务: {review_id}")
    review = _review_from_payload(review_row["payload"])
    task_row = store.get_task(review.task_id)
    if task_row is None:
        raise ValueError(f"未找到标注任务: {review.task_id}")
    task = task_from_dict(task_row["payload"])

    if decision == "skip":
        updated_review = replace(review, status="ignored", answer="skip", meta={**review.meta, "review_note": note})
        store.upsert_review(updated_review)
        return {"status": "ignored", "task_id": task.id}

    if decision == "reject":
        updated_task = _replace_task_review_result(
            task,
            spans=task.spans,
            answer="reject",
            review_id=review.id,
            selected_option_id=selected_option_id or "reject",
            note=note,
            hard_example=hard_example,
        )
        updated_review = replace(
            review,
            status="rejected",
            answer=selected_option_id or "reject",
            meta={**review.meta, "review_note": note, "hard_example": hard_example},
        )
        store.upsert_task(updated_task, project_id=task_row.get("project_id"))
        store.upsert_review(updated_review)
        return {"status": "rejected", "task_id": task.id}

    selected_spans: tuple[AnnotationSpan, ...]
    if decision == "manual" or selected_option_id == "manual":
        selected_spans = tuple(_span_from_payload(span, index) for index, span in enumerate(manual_spans or [], start=1))
        selected_option = "manual"
    else:
        selected_option = selected_option_id or "A"
        prediction = _prediction_for_option(store, review, selected_option)
        selected_spans = prediction.spans

    updated_task = _replace_task_review_result(
        task,
        spans=selected_spans,
        answer="accept",
        review_id=review.id,
        selected_option_id=selected_option,
        note=note,
        hard_example=hard_example,
    )
    updated_review = replace(
        review,
        status="accepted",
        answer=selected_option,
        meta={**review.meta, "review_note": note, "hard_example": hard_example},
    )
    store.upsert_task(updated_task, project_id=task_row.get("project_id"))
    store.upsert_review(updated_review)
    return {"status": "accepted", "task_id": task.id, "selected_option": selected_option}


def _prediction_for_option(store: RuntimeStore, review: ReviewTask, option_id: str) -> Prediction:
    index = ord(option_id.upper()) - ord("A")
    if index < 0 or index >= len(review.prediction_ids):
        raise ValueError(f"无效候选: {option_id}")
    prediction_row = store.get_prediction(review.prediction_ids[index])
    if prediction_row is None:
        raise ValueError(f"候选不存在: {review.prediction_ids[index]}")
    return prediction_from_dict(prediction_row["payload"])


def _replace_task_review_result(
    task: AnnotationTask,
    spans: tuple[AnnotationSpan, ...],
    answer: str,
    review_id: str,
    selected_option_id: str,
    note: str,
    hard_example: bool,
) -> AnnotationTask:
    updated = AnnotationTask(
        id=task.id,
        text=task.text,
        tokens=task.tokens,
        spans=spans,
        relations=task.relations,
        label=task.label,
        options=task.options,
        accept=task.accept,
        answer=answer,
        meta={
            **task.meta,
            "reviewed": True,
            "review_id": review_id,
            "selected_option": selected_option_id,
            "review_note": note,
            "hard_example": hard_example,
        },
    )
    updated.validate()
    return updated


def _span_from_payload(row: dict[str, Any], index: int) -> AnnotationSpan:
    return AnnotationSpan(
        id=str(row.get("id") or f"T{index}"),
        start=int(row.get("start", -1)),
        end=int(row.get("end", -1)),
        text=str(row.get("text", "")),
        label=str(row.get("label", "")),
        implicit=bool(row.get("implicit", False)),
    )


def _review_from_payload(row: dict[str, Any]) -> ReviewTask:
    return ReviewTask(
        id=str(row.get("id", "")),
        task_id=str(row.get("task_id", "")),
        question=str(row.get("question", "")),
        prediction_ids=tuple(row.get("prediction_ids", [])),
        options=tuple(
            AnnotationOption(id=str(option.get("id", "")), text=str(option.get("text", "")))
            for option in row.get("options", [])
        ),
        answer=row.get("answer"),
        status=str(row.get("status", "pending")),
        meta=dict(row.get("meta", {})),
        created_at=str(row.get("created_at", "")),
    )
