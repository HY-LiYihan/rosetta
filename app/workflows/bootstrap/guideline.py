from __future__ import annotations

import json
import re
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

DIAGNOSTIC_PATTERNS = (
    re.compile(r"\bgold-\d+\b", re.IGNORECASE),
    re.compile(r"失败摘要|失败样例|本轮失败|修订建议|漏标|多标|边界不稳定样例|失败/不稳定样例"),
)


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
    clean_description, sanitizer_warnings = sanitize_concept_description(
        str(guideline.get("stable_description") or guideline.get("brief", "")),
        fallback=_compose_description_from_payload(guideline),
    )
    updated_guideline = _guideline_from_payload(guideline, status=status, stable_description=clean_description)
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
            metadata={"sanitizer_warnings": sanitizer_warnings},
        )
    )
    return {
        "status": status,
        "passed": passed,
        "failed": failed,
        "unstable": unstable,
        "summary": f"通过 {len(passed)} 条，失败 {len(failed)} 条，边界不稳定 {len(unstable)} 条。",
    }


def run_concept_refinement_loop(
    store: RuntimeStore,
    guideline_id: str,
    predictor: Predictor | None = None,
    max_rounds: int = 5,
    auto_apply: bool = False,
    temperature: float = 0.0,
) -> dict:
    if max_rounds <= 0:
        raise ValueError("max_rounds must be positive")
    guideline_row = store.get_guideline(guideline_id)
    if guideline_row is None:
        raise ValueError(f"未找到概念阐释: {guideline_id}")
    guideline = guideline_row["payload"]
    gold_sets = store.list_gold_example_sets(guideline_id=guideline_id, limit=1)
    if not gold_sets:
        raise ValueError("该概念还没有金样例库")
    gold_set = gold_sets[0]["payload"]
    target_count = int(gold_set.get("target_count", 15))
    task_ids = list(gold_set.get("task_ids", []))
    if len(task_ids) < target_count:
        raise ValueError(f"正式概念自举需要 {target_count} 条金样例，当前只有 {len(task_ids)} 条")

    current_description, initial_warnings = sanitize_concept_description(
        str(guideline.get("stable_description") or guideline.get("brief", "")),
        fallback=_compose_description_from_payload(guideline),
    )
    initial_clean_description = current_description
    rounds: list[dict] = []
    final_status = "needs_revision"
    final_description = current_description
    next_version = _next_concept_version(store, guideline_id)

    for round_index in range(1, max_rounds + 1):
        round_guideline = {**guideline, "stable_description": current_description}
        result = _evaluate_gold_tasks(store, guideline_id, round_guideline, task_ids, predictor, temperature, round_index)
        failure_summary = _failure_summary(result["details"])
        status = "stable" if not result["failed"] and not result["unstable"] else "needs_revision"
        revision = (
            {
                "description": current_description,
                "raw_response": "",
                "sanitizer_warnings": list(initial_warnings) if round_index == 1 else [],
                "source": "stable_no_revision",
            }
            if status == "stable"
            else revise_concept_description(
                round_guideline,
                result,
                failure_summary,
                predictor=predictor,
                temperature=temperature,
            )
        )
        revised_description = revision["description"]
        version = ConceptVersion(
            id=f"concept-version-{uuid.uuid4().hex[:10]}",
            guideline_id=guideline_id,
            version=next_version,
            description=revised_description,
            failed_task_ids=tuple(result["failed"]),
            unstable_task_ids=tuple(result["unstable"]),
            notes="概念自举校准轮次。",
            metadata={
                "round_index": round_index,
                "pass_count": len(result["passed"]),
                "failed_task_ids": result["failed"],
                "unstable_task_ids": result["unstable"],
                "failure_summary": failure_summary,
                "failure_cases": _failure_cases(result["details"]),
                "raw_revision_response": revision["raw_response"],
                "sanitizer_warnings": revision["sanitizer_warnings"],
                "revision_source": "concept_refinement_loop",
                "revision_mode": revision["source"],
                "auto_generated": True,
                "auto_applied": auto_apply,
            },
        )
        store.upsert_concept_version(version)
        rounds.append(
            {
                "round_index": round_index,
                "status": status,
                "pass_count": len(result["passed"]),
                "failed": result["failed"],
                "unstable": result["unstable"],
                "failure_summary": failure_summary,
                "failure_cases": _failure_cases(result["details"]),
                "raw_revision_response": revision["raw_response"],
                "sanitizer_warnings": revision["sanitizer_warnings"],
                "description": revised_description,
            }
        )
        next_version += 1
        final_status = status
        final_description = revised_description
        if status == "stable":
            break
        current_description = revised_description

    updated_guideline = _guideline_from_payload(
        guideline,
        status="stable" if final_status == "stable" else "needs_revision",
        stable_description=final_description if auto_apply else initial_clean_description if initial_warnings else None,
    )
    store.upsert_guideline(updated_guideline)
    return {
        "status": final_status,
        "rounds": rounds,
        "stable": final_status == "stable",
        "final_description": final_description,
        "auto_applied": auto_apply,
    }


def revise_guideline(guideline: dict, validation_result: dict) -> str:
    revised = _fallback_revised_description(guideline, validation_result)
    cleaned, _warnings = sanitize_concept_description(
        revised,
        fallback=str(guideline.get("stable_description") or guideline.get("brief", "")),
    )
    return cleaned


def revise_concept_description(
    guideline: dict,
    validation_result: dict,
    failure_summary: str,
    predictor: Predictor | None = None,
    temperature: float = 0.0,
) -> dict:
    fallback = _fallback_revised_description(guideline, validation_result)
    if predictor is None:
        cleaned, warnings = sanitize_concept_description(
            fallback,
            fallback=str(guideline.get("stable_description") or guideline.get("brief", "")),
        )
        return {
            "description": cleaned,
            "raw_response": "",
            "sanitizer_warnings": [*warnings, "local_fallback_revision"],
            "source": "local_fallback",
        }

    current_description, input_warnings = sanitize_concept_description(
        str(guideline.get("stable_description") or guideline.get("brief", "")),
        fallback=_compose_description_from_payload(guideline),
    )
    prompt = _build_revision_prompt(current_description, validation_result, failure_summary)
    raw = predictor("你是概念阐释改写助手。只返回最终可用的概念阐释正文。", [{"role": "user", "content": prompt}], temperature)
    cleaned, output_warnings = sanitize_concept_description(raw, fallback=fallback)
    return {
        "description": cleaned,
        "raw_response": raw,
        "sanitizer_warnings": [*input_warnings, *output_warnings],
        "source": "llm_revision",
    }


def sanitize_concept_description(text: str, fallback: str = "") -> tuple[str, list[str]]:
    warnings: list[str] = []
    raw = str(text or "").strip()
    if not raw:
        return str(fallback or "").strip(), ["empty_revision_response"]

    candidate = _extract_revision_text(raw, warnings)
    lines = candidate.splitlines()
    start_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().startswith(("概念描述：", "Concept description:", "Concept Description:"))
        ),
        None,
    )
    if start_index is not None:
        lines = lines[start_index:]

    cleaned_lines: list[str] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
        if _contains_diagnostic_text(stripped):
            warnings.append(f"removed_diagnostic_line:{index + 1}")
            continue
        if index <= 2 and _looks_like_preface(stripped):
            warnings.append(f"removed_preface_line:{index + 1}")
            continue
        cleaned_lines.append(line.rstrip())

    cleaned = "\n".join(cleaned_lines).strip()
    removed_diagnostics = any(warning.startswith("removed_diagnostic_line") for warning in warnings)
    if not cleaned or _contains_diagnostic_text(cleaned) or (removed_diagnostics and not _has_minimum_guideline_shape(cleaned)):
        warnings.append("fallback_to_previous_description")
        cleaned = str(fallback or "").strip()
    return cleaned, warnings


def _evaluate_gold_tasks(
    store: RuntimeStore,
    guideline_id: str,
    guideline: dict,
    task_ids: list[str],
    predictor: Predictor | None,
    temperature: float,
    round_index: int,
) -> dict:
    passed: list[str] = []
    failed: list[str] = []
    unstable: list[str] = []
    details: list[dict] = []
    for task_id in task_ids:
        task_row = store.get_task(task_id)
        if task_row is None:
            failed.append(task_id)
            details.append({"task_id": task_id, "route": "failed", "reason": "任务不存在"})
            continue
        task_payload = task_row["payload"]
        prediction_payload = _predict_guideline(guideline, task_payload, predictor, temperature)
        detail = _gold_comparison_detail(task_payload, prediction_payload, prediction_payload["route"])
        prediction = Prediction(
            id=f"pred-{uuid.uuid4().hex[:10]}",
            task_id=task_id,
            source="concept_refinement",
            model=prediction_payload.get("model", "local-rule"),
            spans=tuple(prediction_payload.get("predicted_spans", ())),
            score=prediction_payload["score"],
            raw_response=prediction_payload["raw_response"],
            meta={
                "guideline_id": guideline_id,
                "round_index": round_index,
                "route": prediction_payload["route"],
                "failure_detail": detail,
            },
        )
        store.upsert_prediction(prediction)
        details.append({"task_id": task_id, **detail})
        if prediction_payload["route"] == "passed":
            passed.append(task_id)
        elif prediction_payload["route"] == "unstable":
            unstable.append(task_id)
        else:
            failed.append(task_id)
    return {"passed": passed, "failed": failed, "unstable": unstable, "details": details}


def _gold_comparison_detail(task_payload: dict, prediction_payload: dict, route: str) -> dict:
    gold_keys = {_span_key_from_dict(span) for span in task_payload.get("spans", [])}
    pred_keys = {_span_key(span) for span in prediction_payload.get("predicted_spans", [])}
    missing = sorted(gold_keys - pred_keys)
    extra = sorted(pred_keys - gold_keys)
    return {
        "route": route,
        "score": prediction_payload.get("score", 0.0),
        "missing_spans": [_span_key_to_dict(key) for key in missing],
        "extra_spans": [_span_key_to_dict(key) for key in extra],
    }


def _failure_summary(details: list[dict]) -> str:
    failed = [detail for detail in details if detail.get("route") != "passed"]
    if not failed:
        return "所有金样例均通过当前概念阐释。"
    lines = []
    for detail in failed[:8]:
        missing = detail.get("missing_spans", [])
        extra = detail.get("extra_spans", [])
        parts = []
        if missing:
            parts.append("漏标 " + ", ".join(item["text"] for item in missing[:3]))
        if extra:
            parts.append("多标 " + ", ".join(item["text"] for item in extra[:3]))
        lines.append(f"{detail['task_id']}: " + ("；".join(parts) if parts else "标注边界或标签不稳定"))
    return "\n".join(lines)


def _failure_cases(details: list[dict]) -> list[dict]:
    return [detail for detail in details if detail.get("route") != "passed"]


def _fallback_revised_description(guideline: dict, validation_result: dict) -> str:
    base, _warnings = sanitize_concept_description(
        str(guideline.get("stable_description") or guideline.get("brief", "")),
        fallback=_compose_description_from_payload(guideline),
    )
    if "边界补充：" in base or "Boundary supplement:" in base:
        return base
    supplement = (
        "边界补充：应纳入与任务领域直接相关、在原文中明确出现且具有专业概念含义的完整片段；"
        "多词术语保持整体边界；普通泛化词、人物机构名、新闻来源和非术语性修饰语不纳入。"
    )
    return f"{base}\n{supplement}" if base else supplement


def _build_revision_prompt(current_description: str, validation_result: dict, failure_summary: str) -> str:
    missing_terms, extra_terms = _revision_terms(validation_result.get("details", []))
    failed_count = len(validation_result.get("failed", []))
    unstable_count = len(validation_result.get("unstable", []))
    missing_line = "；".join(missing_terms[:12]) or "无"
    extra_line = "；".join(extra_terms[:8]) or "无"
    return f"""请根据金样例校准结果，优化下面的概念阐释。

你的任务很简单：只返回优化后的概念阐释正文，不要返回解释、分析过程或列表化日志。

当前概念阐释：
{current_description}

需要吸收进概念阐释的现象（只供理解，不要原样复述）：
- 需要更明确纳入的片段类型：{missing_line}
- 需要更明确排除或收紧边界的片段类型：{extra_line}
- 受影响样例数量：未通过 {failed_count} 条，边界不稳定 {unstable_count} 条。

输出要求：
1. 只输出可以直接用于下一轮标注的概念阐释正文。
2. 保持“概念描述 / 标签集合 / 边界规则 / 排除规则 / 输出格式”这类清晰字段。
3. 不要输出解释、失败样例编号、失败摘要或修订日志。
4. 不要出现 gold-编号、“失败摘要”、“本轮失败”、“修订建议”、“漏标”、“多标”、“边界不稳定样例”等诊断文字。"""


def _revision_terms(details: list[dict]) -> tuple[list[str], list[str]]:
    missing_terms: list[str] = []
    extra_terms: list[str] = []
    for detail in details:
        if detail.get("route") == "passed":
            continue
        missing_terms.extend(str(item.get("text", "")).strip() for item in detail.get("missing_spans", []))
        extra_terms.extend(str(item.get("text", "")).strip() for item in detail.get("extra_spans", []))
    return _dedupe_nonempty(missing_terms), _dedupe_nonempty(extra_terms)


def _dedupe_nonempty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _extract_revision_text(raw: str, warnings: list[str]) -> str:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        for key in ("optimized_description", "description", "final_description", "guideline"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                warnings.append(f"extracted_json_field:{key}")
                return value.strip()
        warnings.append("unsupported_json_revision_response")
        return ""

    if "```" not in raw:
        return raw
    fenced = re.findall(r"```(?:\w+)?\s*(.*?)```", raw, flags=re.DOTALL)
    if fenced:
        warnings.append("extracted_markdown_fence")
        return fenced[0].strip()
    return raw.replace("```", "").strip()


def _contains_diagnostic_text(text: str) -> bool:
    return any(pattern.search(text) for pattern in DIAGNOSTIC_PATTERNS)


def _looks_like_preface(line: str) -> bool:
    prefixes = (
        "以下是",
        "下面是",
        "这里是",
        "已根据",
        "我已",
        "好的",
        "Here is",
        "Below is",
        "I have",
        "Explanation",
        "Change log",
    )
    return line.startswith(prefixes)


def _has_minimum_guideline_shape(text: str) -> bool:
    has_description = "概念描述：" in text or "Concept description:" in text or "Concept Description:" in text
    supporting_fields = (
        "标签集合：",
        "边界规则：",
        "排除规则：",
        "输出格式：",
        "Labels:",
        "Boundary",
        "Negative",
        "Output",
    )
    return has_description and any(field in text for field in supporting_fields)


def _compose_description_from_payload(payload: dict) -> str:
    return _compose_description(
        brief=str(payload.get("brief", "")),
        labels=[str(label) for label in payload.get("labels", [])],
        boundary_rules=[str(rule) for rule in payload.get("boundary_rules", [])],
        negative_rules=[str(rule) for rule in payload.get("negative_rules", [])],
        output_format=str(payload.get("output_format", "[原文]{标签}")),
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
        predicted_spans = tuple(_span_from_dict(span, index) for index, span in enumerate(task_payload.get("spans", []), start=1))
        return {
            "score": score,
            "route": route,
            "raw_response": json.dumps({"span_count": span_count}),
            "model": "local-rule",
            "predicted_spans": predicted_spans,
        }

    prompt = f"""请只根据以下概念阐释标注文本，不要参考金答案。

概念阐释：
{guideline.get('stable_description') or guideline.get('brief')}

文本：
{task_payload['text']}

请只输出 JSON，字段为 text、annotation、explanation。"""
    raw = predictor("你是严谨的标注校验助手，只输出 JSON。", [{"role": "user", "content": prompt}], temperature)
    parsed, warning = parse_annotation_response(raw)
    if warning or not parsed:
        return {"score": 0.2, "route": "failed", "raw_response": raw, "model": "llm", "predicted_spans": ()}
    predicted_spans = parsed.get("annotation", {}).get("layers", {}).get("spans", [])
    gold_spans = task_payload.get("spans", [])
    gold_set = {_span_key_from_dict(span) for span in gold_spans}
    pred_set = {_span_key_from_dict(span) for span in predicted_spans}
    score = len(gold_set & pred_set) / len(gold_set) if gold_set else 0.0
    route = "passed" if score >= 1.0 else "unstable" if score >= 0.5 else "failed"
    return {
        "score": round(score, 4),
        "route": route,
        "raw_response": raw,
        "model": "llm",
        "predicted_spans": tuple(_span_from_dict(span, index) for index, span in enumerate(predicted_spans, start=1)),
    }


def _guideline_from_payload(payload: dict, status: str, stable_description: str | None = None) -> ConceptGuideline:
    return ConceptGuideline(
        id=str(payload["id"]),
        project_id=str(payload["project_id"]),
        name=str(payload["name"]),
        brief=str(payload["brief"]),
        labels=tuple(payload.get("labels", [])),
        boundary_rules=tuple(payload.get("boundary_rules", [])),
        negative_rules=tuple(payload.get("negative_rules", [])),
        output_format=str(payload.get("output_format", "[原文]{标签}")),
        stable_description=stable_description
        if stable_description is not None
        else str(payload.get("stable_description") or payload.get("brief", "")),
        status=status,
        metadata=dict(payload.get("metadata", {})),
        created_at=str(payload.get("created_at", "")) or utc_timestamp(),
    )


def _next_concept_version(store: RuntimeStore, guideline_id: str) -> int:
    versions = store.list_concept_versions(guideline_id=guideline_id, limit=1000)
    return max((int(row["payload"].get("version", 0)) for row in versions), default=0) + 1


def _span_from_dict(row: dict, index: int) -> AnnotationSpan:
    return AnnotationSpan(
        id=str(row.get("id") or f"T{index}"),
        start=int(row.get("start", -1)),
        end=int(row.get("end", -1)),
        text=str(row.get("text", "")),
        label=str(row.get("label", "")),
        implicit=bool(row.get("implicit", False)),
    )


def _span_key(span: AnnotationSpan) -> tuple[int, int, str, str, bool]:
    return (span.start, span.end, span.text, span.label, span.implicit)


def _span_key_from_dict(span: dict) -> tuple[int, int, str, str, bool]:
    return (
        int(span.get("start", -1)),
        int(span.get("end", -1)),
        str(span.get("text", "")),
        str(span.get("label", "")),
        bool(span.get("implicit", False)),
    )


def _span_key_to_dict(key: tuple[int, int, str, str, bool]) -> dict:
    start, end, text, label, implicit = key
    return {"start": start, "end": end, "text": text, "label": label, "implicit": implicit}
