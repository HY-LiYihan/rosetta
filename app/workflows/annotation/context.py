from __future__ import annotations

import re
from typing import Any

from app.domain.annotation_doc import spans_to_legacy_string
from app.runtime.store import RuntimeStore

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def build_annotation_context(
    store: RuntimeStore,
    guideline_id: str,
    task_id: str,
    similar_k: int = 4,
    boundary_k: int = 2,
    failure_k: int = 5,
) -> dict[str, Any]:
    guideline_row = store.get_guideline(guideline_id)
    if guideline_row is None:
        raise ValueError(f"未找到概念阐释: {guideline_id}")
    task_row = store.get_task(task_id)
    if task_row is None:
        raise ValueError(f"未找到标注任务: {task_id}")

    guideline = guideline_row["payload"]
    task = task_row["payload"]
    examples = _example_pool(store, guideline)
    scored = [
        (example, lexical_similarity(task["text"], example["text"]))
        for example in examples
        if example["id"] != task_id
    ]
    similar = [
        example
        for example, _score in sorted(scored, key=lambda item: (-item[1], item[0]["id"]))[: max(0, similar_k)]
    ]
    similar_ids = {example["id"] for example in similar}
    boundary = [
        example
        for example, _score in sorted(
            [(example, score) for example, score in scored if example["id"] not in similar_ids],
            key=lambda item: (item[1], item[0]["id"]),
        )[: max(0, boundary_k)]
    ]
    failure_memory = _failure_memory(store, guideline_id, failure_k)
    prompt = _compose_context_prompt(guideline, similar, boundary, failure_memory)
    context_examples = [*_examples_for_prompt(similar, "similar"), *_examples_for_prompt(boundary, "boundary")]
    return {
        "guideline": guideline,
        "task": task,
        "prompt": prompt,
        "similar_examples": similar,
        "boundary_examples": boundary,
        "failure_memory": failure_memory,
        "examples": context_examples,
        "context_example_ids": [example["id"] for example in [*similar, *boundary]],
    }


def lexical_similarity(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return round(len(left_tokens & right_tokens) / len(left_tokens | right_tokens), 4)


def _example_pool(store: RuntimeStore, guideline: dict) -> list[dict[str, Any]]:
    pool: dict[str, dict[str, Any]] = {}
    for gold_set in store.list_gold_example_sets(guideline_id=guideline["id"], limit=20):
        for task_id in gold_set["payload"].get("task_ids", []):
            task_row = store.get_task(task_id)
            if task_row:
                payload = dict(task_row["payload"])
                payload.setdefault("meta", {})
                payload["meta"] = {**payload["meta"], "source_pool": "gold"}
                pool[payload["id"]] = payload

    project_id = guideline.get("project_id")
    for row in store.list_tasks(project_id=project_id, limit=5000):
        payload = row["payload"]
        meta = payload.get("meta", {})
        is_high_confidence = meta.get("route") == "auto_accept" and float(meta.get("score", 0.0)) >= 0.8
        is_gold_like = meta.get("promote_to_gold") or meta.get("source_pool") == "gold_like"
        if not payload.get("spans") or not (is_high_confidence or is_gold_like):
            continue
        copied = dict(payload)
        copied["meta"] = {**meta, "source_pool": "high_confidence" if is_high_confidence else "gold_like"}
        pool[copied["id"]] = copied
    return list(pool.values())


def _examples_for_prompt(examples: list[dict[str, Any]], role: str) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for example in examples:
        output.append(
            {
                "text": example["text"],
                "annotation": spans_to_legacy_string(example.get("spans", [])),
                "explanation": f"{role} example from {example.get('meta', {}).get('source_pool', 'example')}",
            }
        )
    return output


def _failure_memory(store: RuntimeStore, guideline_id: str, limit: int) -> list[str]:
    memory: list[str] = []
    for row in store.list_concept_versions(guideline_id=guideline_id, limit=100):
        metadata = row["payload"].get("metadata", {})
        summary = metadata.get("failure_summary")
        if summary and summary not in memory:
            memory.append(str(summary))
        if len(memory) >= limit:
            return memory[:limit]

    for review in store.list_reviews(limit=5000):
        meta = review["payload"].get("meta", {})
        if not meta.get("hard_example") and review["payload"].get("status") != "rejected":
            continue
        note = meta.get("review_note") or meta.get("error_type") or meta.get("route_reason")
        if note and note not in memory:
            memory.append(str(note))
        if len(memory) >= limit:
            break
    return memory[:limit]


def _compose_context_prompt(
    guideline: dict,
    similar: list[dict[str, Any]],
    boundary: list[dict[str, Any]],
    failure_memory: list[str],
) -> str:
    sections = [guideline.get("stable_description") or guideline.get("brief", "")]
    if similar:
        sections.append(f"相似或高置信参考样例数量：{len(similar)}。优先保持与这些样例一致的标签和边界。")
    if boundary:
        sections.append(f"边界远例数量：{len(boundary)}。这些样例用于提醒不要过度泛化。")
    if failure_memory:
        sections.append("近期失败模式：\n" + "\n".join(f"- {item}" for item in failure_memory[:5]))
    sections.append(f"模型输出格式：{guideline.get('output_format', '[原文]{标签}')}")
    return "\n\n".join(section for section in sections if section)


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}
