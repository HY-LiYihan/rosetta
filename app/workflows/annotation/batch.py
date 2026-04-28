from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha1
from typing import Callable

from app.core.models import (
    AnnotationOption,
    AnnotationSpan,
    AnnotationTask,
    BatchJob,
    BatchJobItem,
    Prediction,
    ReviewTask,
    utc_timestamp,
)
from app.data.prodigy_jsonl import task_from_dict
from app.runtime.store import RuntimeStore
from app.services.annotation_service import build_annotation_prompt, parse_annotation_response

Predictor = Callable[[str, list[dict], float], str]


def submit_batch_annotation(
    store: RuntimeStore,
    project_id: str,
    guideline_id: str,
    tasks: list[AnnotationTask],
    sample_count: int = 5,
    concurrency: int = 4,
    review_threshold: float = 0.75,
    auto_sample_rate: float = 0.05,
    metadata: dict | None = None,
) -> BatchJob:
    job = BatchJob(
        id=f"job-{uuid.uuid4().hex[:10]}",
        project_id=project_id,
        guideline_id=guideline_id,
        sample_count=sample_count,
        concurrency=concurrency,
        review_threshold=review_threshold,
        auto_sample_rate=auto_sample_rate,
        total_items=len(tasks),
        metadata=metadata or {},
    )
    store.upsert_job(job)
    for task in tasks:
        store.upsert_task(task, project_id=project_id)
        store.upsert_job_item(BatchJobItem(id=f"item-{uuid.uuid4().hex[:10]}", job_id=job.id, task_id=task.id))
    store.add_job_event(job.id, "submitted", {"total_items": len(tasks)})
    return job


def run_batch_worker(
    store: RuntimeStore,
    job_id: str,
    predictor: Predictor,
    platform: str,
    model: str,
    temperature: float = 0.3,
) -> dict:
    job_row = store.get_job(job_id)
    if job_row is None:
        raise ValueError(f"未找到批量任务: {job_id}")
    job = _job_from_payload(job_row["payload"], status="running")
    store.upsert_job(job)
    pending_items = store.list_job_items(job_id=job_id, status="queued", limit=10000)
    guideline_row = store.get_guideline(job.guideline_id)
    if guideline_row is None:
        raise ValueError("批量任务缺少概念阐释")
    guideline = guideline_row["payload"]

    completed = 0
    failed = 0
    review_count = 0
    with ThreadPoolExecutor(max_workers=job.concurrency) as pool:
        future_map = {
            pool.submit(_run_one_item, store, job, item, guideline, predictor, platform, model, temperature): item
            for item in pending_items
        }
        for future in as_completed(future_map):
            item = future_map[future]
            try:
                result = future.result()
                completed += 1
                if result["route"] == "review":
                    review_count += 1
                store.add_job_event(job_id, "item_completed", {"item_id": item["id"], **result})
            except Exception as exc:
                failed += 1
                failed_item = _job_item_from_payload(item["payload"], status="failed", error=str(exc))
                store.upsert_job_item(failed_item)
                store.add_job_event(job_id, "item_failed", {"item_id": item["id"], "error": str(exc)})

    final_status = "completed" if failed == 0 else "failed"
    final_job = _job_from_payload(
        job_row["payload"],
        status=final_status,
        completed_items=completed,
        failed_items=failed,
        review_items=review_count,
    )
    store.upsert_job(final_job)
    store.add_job_event(job_id, final_status, {"completed": completed, "failed": failed, "review": review_count})
    return {
        "job_id": job_id,
        "status": final_status,
        "completed_items": completed,
        "failed_items": failed,
        "review_items": review_count,
    }


def score_candidates(predictions: list[Prediction]) -> dict:
    if not predictions:
        return {"score": 0.0, "agreement": 0.0, "avg_confidence": 0.0, "route_reason": "无候选"}
    signatures = [_prediction_signature(prediction) for prediction in predictions]
    best_count = max(signatures.count(signature) for signature in signatures)
    agreement = best_count / len(signatures)
    confidences = [prediction.score for prediction in predictions if prediction.score is not None]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
    score = round((agreement * 0.7) + (avg_confidence * 0.3), 4)
    return {
        "score": score,
        "agreement": round(agreement, 4),
        "avg_confidence": round(avg_confidence, 4),
        "route_reason": "自洽性与模型自评分组合",
    }


def _run_one_item(
    store: RuntimeStore,
    job: BatchJob,
    item_row: dict,
    guideline: dict,
    predictor: Predictor,
    platform: str,
    model: str,
    temperature: float,
) -> dict:
    item = _job_item_from_payload(item_row["payload"], status="running")
    store.upsert_job_item(item)
    task_row = store.get_task(item.task_id)
    if task_row is None:
        raise ValueError(f"未找到任务: {item.task_id}")
    task = task_from_dict(task_row["payload"])
    concept = {
        "name": guideline.get("name", "概念"),
        "prompt": guideline.get("stable_description") or guideline.get("brief", ""),
        "examples": [],
    }
    predictions: list[Prediction] = []
    for run_index in range(job.sample_count):
        raw = predictor(
            "你是严谨的批量标注助手，只输出 JSON。",
            [{"role": "user", "content": build_annotation_prompt(concept, task.text)}],
            temperature,
        )
        parsed, warning = parse_annotation_response(raw)
        spans = _spans_from_parsed(parsed, source_text=task.text)
        confidence = _confidence_from_raw(raw, default=0.7 if parsed and not warning else 0.2)
        prediction = Prediction(
            id=f"pred-{uuid.uuid4().hex[:10]}",
            task_id=task.id,
            source="batch",
            model=model,
            spans=tuple(spans),
            score=confidence,
            raw_response=raw,
            meta={"job_id": job.id, "run_index": run_index + 1, "parse_warning": warning or ""},
        )
        store.upsert_prediction(prediction)
        predictions.append(prediction)

    score = score_candidates(predictions)
    audit_sample = _should_audit_sample(job, task)
    route = "auto_accept" if score["score"] >= job.review_threshold and not audit_sample else "review"
    route_reason = "高置信抽检" if audit_sample and score["score"] >= job.review_threshold else score["route_reason"]
    best_prediction = _best_prediction(predictions)
    updated_task = _task_with_route(task, best_prediction, route, score, route_reason)
    store.upsert_task(updated_task, project_id=job.project_id)
    if route == "review":
        review = _build_review_task(task, predictions, score, job, route_reason)
        store.upsert_review(review)
    completed_item = _job_item_from_payload(item_row["payload"], status="completed", score=score["score"], route=route)
    store.upsert_job_item(completed_item)
    return {"task_id": task.id, "score": score["score"], "route": route}


def _spans_from_parsed(parsed: dict | None, source_text: str = "") -> list[AnnotationSpan]:
    if not parsed:
        return []
    spans = parsed.get("annotation", {}).get("layers", {}).get("spans", [])
    output: list[AnnotationSpan] = []
    for index, span in enumerate(spans, start=1):
        implicit = bool(span.get("implicit", False))
        text = str(span.get("text", ""))
        start = int(span.get("start", -1))
        end = int(span.get("end", -1))
        if implicit:
            start = -1
            end = -1
        if source_text and not implicit:
            located = source_text.find(text)
            if located >= 0:
                start = located
                end = located + len(text)
        if start < 0 and not implicit:
            continue
        output.append(
            AnnotationSpan(
                id=str(span.get("id") or f"T{index}"),
                start=start,
                end=end,
                text=text,
                label=str(span.get("label", "")),
                implicit=implicit,
            )
        )
    return output


def _confidence_from_raw(raw: str, default: float) -> float:
    try:
        payload = json.loads(raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
        value = payload.get("confidence", payload.get("model_confidence", default))
        confidence = float(value)
    except Exception:
        confidence = default
    return round(max(0.0, min(1.0, confidence)), 4)


def _prediction_signature(prediction: Prediction) -> tuple:
    return tuple((span.start, span.end, span.text, span.label) for span in prediction.spans)


def _best_prediction(predictions: list[Prediction]) -> Prediction | None:
    return max(predictions, key=lambda prediction: prediction.score or 0.0) if predictions else None


def _task_with_route(
    task: AnnotationTask,
    prediction: Prediction | None,
    route: str,
    score: dict,
    route_reason: str,
) -> AnnotationTask:
    return AnnotationTask(
        id=task.id,
        text=task.text,
        tokens=task.tokens,
        spans=prediction.spans if prediction else task.spans,
        relations=task.relations,
        label=task.label,
        options=task.options,
        accept=task.accept,
        answer="accept" if route == "auto_accept" else None,
        meta={
            **task.meta,
            "route": route,
            "score": score["score"],
            "agreement": score["agreement"],
            "avg_confidence": score["avg_confidence"],
            "route_reason": route_reason,
        },
    )


def _build_review_task(
    task: AnnotationTask,
    predictions: list[Prediction],
    score: dict,
    job: BatchJob,
    route_reason: str,
) -> ReviewTask:
    options = [
        AnnotationOption(
            id=chr(ord("A") + index),
            text="; ".join(f"{span.text} / {span.label}" for span in prediction.spans) or "空标注",
        )
        for index, prediction in enumerate(predictions[:5])
    ]
    options.append(AnnotationOption(id="manual", text="以上都不对，我要手动修正"))
    return ReviewTask(
        id=f"review-{uuid.uuid4().hex[:10]}",
        task_id=task.id,
        question="请选择最符合概念阐释的候选标注。",
        prediction_ids=tuple(prediction.id for prediction in predictions),
        options=tuple(options),
        status="pending",
        meta={
            "job_id": job.id,
            "score": score["score"],
            "agreement": score["agreement"],
            "avg_confidence": score["avg_confidence"],
            "route_reason": route_reason,
            "source_text": task.text,
        },
    )


def _job_from_payload(payload: dict, **updates) -> BatchJob:
    data = {**payload, **updates}
    return BatchJob(
        id=data["id"],
        project_id=data["project_id"],
        guideline_id=data["guideline_id"],
        status=data.get("status", "queued"),
        sample_count=int(data.get("sample_count", 5)),
        concurrency=int(data.get("concurrency", 4)),
        review_threshold=float(data.get("review_threshold", 0.75)),
        auto_sample_rate=float(data.get("auto_sample_rate", 0.05)),
        total_items=int(data.get("total_items", 0)),
        completed_items=int(data.get("completed_items", 0)),
        failed_items=int(data.get("failed_items", 0)),
        review_items=int(data.get("review_items", 0)),
        metadata=dict(data.get("metadata", {})),
        created_at=data.get("created_at") or utc_timestamp(),
        updated_at=utc_timestamp(),
    )


def _job_item_from_payload(payload: dict, **updates) -> BatchJobItem:
    data = {**payload, **updates}
    return BatchJobItem(
        id=data["id"],
        job_id=data["job_id"],
        task_id=data["task_id"],
        status=data.get("status", "queued"),
        score=float(data["score"]) if data.get("score") is not None else None,
        route=data.get("route", "pending"),
        error=data.get("error", ""),
        metadata=dict(data.get("metadata", {})),
        created_at=data.get("created_at") or utc_timestamp(),
        updated_at=utc_timestamp(),
    )


def _should_audit_sample(job: BatchJob, task: AnnotationTask) -> bool:
    if job.auto_sample_rate <= 0:
        return False
    digest = sha1(f"{job.id}:{task.id}".encode("utf-8")).hexdigest()
    value = int(digest[:8], 16) / 0xFFFFFFFF
    return value < job.auto_sample_rate
