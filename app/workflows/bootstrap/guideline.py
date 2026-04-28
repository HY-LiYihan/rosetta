from __future__ import annotations

import json
import uuid
from typing import Callable

from app.core.models import (
    AnnotationSpan,
    AnnotationTask,
    ConceptGuideline,
    ConceptVersion,
    GoldExampleSet,
    Prediction,
    utc_timestamp,
)
from app.domain.annotation_doc import legacy_string_to_spans
from app.runtime.store import RuntimeStore
from app.services.annotation_service import parse_annotation_response

Predictor = Callable[[str, list[dict], float], str]


def build_guideline(
    project_id: str,
    name: str,
    brief: str,
    labels: list[str],
    boundary_rules: list[str],
    negative_rules: list[str],
    output_format: str = "[原文]{标签}",
) -> ConceptGuideline:
    guideline_id = f"guide-{uuid.uuid4().hex[:10]}"
    stable_description = _compose_description(brief, labels, boundary_rules, negative_rules, output_format)
    return ConceptGuideline(
        id=guideline_id,
        project_id=project_id,
        name=name,
        brief=brief,
        labels=tuple(labels),
        boundary_rules=tuple(boundary_rules),
        negative_rules=tuple(negative_rules),
        output_format=output_format,
        stable_description=stable_description,
    )


def gold_task_from_markup(task_id: str, text: str, annotation_markup: str, label_hint: str = "") -> AnnotationTask:
    spans = []
    for span in legacy_string_to_spans(text, annotation_markup):
        implicit = bool(span.get("implicit", False))
        start = int(span.get("start", -1))
        end = int(span.get("end", -1))
        spans.append(
            AnnotationSpan(
                id=str(span.get("id", f"T{len(spans)+1}")),
                start=start,
                end=end,
                text=str(span.get("text", "")),
                label=str(span.get("label") or label_hint or "Concept"),
                implicit=implicit,
            )
        )
    task = AnnotationTask(
        id=task_id,
        text=text,
        spans=tuple(spans),
        answer="accept",
        meta={"source": "gold", "runtime_annotation": annotation_markup},
    )
    task.validate()
    return task


def save_guideline_package(
    store: RuntimeStore,
    project_id: str,
    name: str,
    brief: str,
    labels: list[str],
    boundary_rules: list[str],
    negative_rules: list[str],
    gold_tasks: list[AnnotationTask],
) -> dict:
    guideline = build_guideline(project_id, name, brief, labels, boundary_rules, negative_rules)
    store.upsert_guideline(guideline)
    for task in gold_tasks:
        store.upsert_task(task, project_id=project_id)
    gold_set = GoldExampleSet(
        id=f"gold-{uuid.uuid4().hex[:10]}",
        project_id=project_id,
        guideline_id=guideline.id,
        task_ids=tuple(task.id for task in gold_tasks),
        status="draft" if len(gold_tasks) < 15 else "validating",
    )
    store.upsert_gold_example_set(gold_set)
    version = ConceptVersion(
        id=f"concept-version-{uuid.uuid4().hex[:10]}",
        guideline_id=guideline.id,
        version=1,
        description=guideline.stable_description,
        notes="初始概念阐释。",
    )
    store.upsert_concept_version(version)
    return {"guideline": guideline, "gold_set": gold_set, "version": version}


def validate_gold_examples(
    store: RuntimeStore,
    guideline_id: str,
    predictor: Predictor | None = None,
    temperature: float = 0.0,
) -> dict:
    guideline_row = store.get_guideline(guideline_id)
    if guideline_row is None:
        raise ValueError(f"未找到概念阐释: {guideline_id}")
    guideline = guideline_row["payload"]
    gold_sets = store.list_gold_example_sets(guideline_id=guideline_id, limit=1)
    if not gold_sets:
        raise ValueError("该概念还没有金样例库")

    passed: list[str] = []
    failed: list[str] = []
    unstable: list[str] = []
    for task_id in gold_sets[0]["payload"]["task_ids"]:
        task_row = store.get_task(task_id)
        if task_row is None:
            failed.append(task_id)
            continue
        task_payload = task_row["payload"]
        prediction_payload = _predict_guideline(guideline, task_payload, predictor, temperature)
        prediction = Prediction(
            id=f"pred-{uuid.uuid4().hex[:10]}",
            task_id=task_id,
            source="guideline_validation",
            model=prediction_payload.get("model", "local-rule"),
            score=prediction_payload["score"],
            raw_response=prediction_payload["raw_response"],
            meta={"guideline_id": guideline_id, "route": prediction_payload["route"]},
        )
        store.upsert_prediction(prediction)
        if prediction_payload["route"] == "passed":
            passed.append(task_id)
        elif prediction_payload["route"] == "unstable":
            unstable.append(task_id)
        else:
            failed.append(task_id)

    status = "stable" if not failed and not unstable else "needs_revision"
    updated_guideline = _guideline_from_payload(guideline, status=status)
    store.upsert_guideline(updated_guideline)
    versions = store.list_concept_versions(guideline_id=guideline_id, limit=1000)
    next_version = max((int(row["payload"].get("version", 0)) for row in versions), default=0) + 1
    store.upsert_concept_version(
        ConceptVersion(
            id=f"concept-version-{uuid.uuid4().hex[:10]}",
            guideline_id=guideline_id,
            version=next_version,
            description=updated_guideline.stable_description,
            failed_task_ids=tuple(failed),
            unstable_task_ids=tuple(unstable),
            notes="概念验证结果。",
        )
    )
    return {
        "status": status,
        "passed": passed,
        "failed": failed,
        "unstable": unstable,
        "summary": f"通过 {len(passed)} 条，失败 {len(failed)} 条，边界不稳定 {len(unstable)} 条。",
    }


def revise_guideline(guideline: dict, validation_result: dict) -> str:
    failed = ", ".join(validation_result.get("failed", [])) or "无"
    unstable = ", ".join(validation_result.get("unstable", [])) or "无"
    return (
        f"{guideline.get('stable_description') or guideline.get('brief', '')}\n\n"
        "修订建议：\n"
        f"1. 明确失败样例范围：{failed}。\n"
        f"2. 对边界不稳定样例增加排除条件：{unstable}。\n"
        "3. 标注时必须只标出符合概念定义且能在原文中定位的片段；边界不完整时优先进入人工审核。"
    )


def _compose_description(
    brief: str,
    labels: list[str],
    boundary_rules: list[str],
    negative_rules: list[str],
    output_format: str,
) -> str:
    return "\n".join(
        [
            f"概念描述：{brief.strip()}",
            f"标签集合：{', '.join(labels) if labels else 'Concept'}",
            "边界规则：" + ("；".join(rule for rule in boundary_rules if rule) or "按最小完整语义片段标注。"),
            "排除规则：" + ("；".join(rule for rule in negative_rules if rule) or "不标注泛化、比喻或证据不足的片段。"),
            f"输出格式：{output_format}",
        ]
    )


def _predict_guideline(guideline: dict, task_payload: dict, predictor: Predictor | None, temperature: float) -> dict:
    if predictor is None:
        span_count = len(task_payload.get("spans", []))
        score = 1.0 if span_count else 0.4
        route = "passed" if score >= 0.9 else "failed"
        return {"score": score, "route": route, "raw_response": json.dumps({"span_count": span_count}), "model": "local-rule"}

    prompt = f"""请只根据以下概念阐释标注文本，不要参考金答案。

概念阐释：
{guideline.get('stable_description') or guideline.get('brief')}

文本：
{task_payload['text']}

请只输出 JSON，字段为 text、annotation、explanation。"""
    raw = predictor("你是严谨的标注校验助手，只输出 JSON。", [{"role": "user", "content": prompt}], temperature)
    parsed, warning = parse_annotation_response(raw)
    if warning or not parsed:
        return {"score": 0.2, "route": "failed", "raw_response": raw, "model": "llm"}
    predicted_spans = parsed.get("annotation", {}).get("layers", {}).get("spans", [])
    gold_spans = task_payload.get("spans", [])
    gold_set = {(span["text"], span["label"]) for span in gold_spans}
    pred_set = {(span["text"], span["label"]) for span in predicted_spans}
    score = len(gold_set & pred_set) / len(gold_set) if gold_set else 0.0
    route = "passed" if score >= 1.0 else "unstable" if score >= 0.5 else "failed"
    return {"score": round(score, 4), "route": route, "raw_response": raw, "model": "llm"}


def _guideline_from_payload(payload: dict, status: str) -> ConceptGuideline:
    return ConceptGuideline(
        id=str(payload["id"]),
        project_id=str(payload["project_id"]),
        name=str(payload["name"]),
        brief=str(payload["brief"]),
        labels=tuple(payload.get("labels", [])),
        boundary_rules=tuple(payload.get("boundary_rules", [])),
        negative_rules=tuple(payload.get("negative_rules", [])),
        output_format=str(payload.get("output_format", "[原文]{标签}")),
        stable_description=str(payload.get("stable_description") or payload.get("brief", "")),
        status=status,
        metadata=dict(payload.get("metadata", {})),
        created_at=str(payload.get("created_at", "")) or utc_timestamp(),
    )
