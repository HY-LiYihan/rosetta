from __future__ import annotations

import json
from collections import Counter
from typing import Any


def rows_to_jsonl(rows: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(row["payload"], ensure_ascii=False) for row in rows) + ("\n" if rows else "")


def filter_tasks_for_export(tasks: list[dict[str, Any]], export_kind: str) -> list[dict[str, Any]]:
    if export_kind == "all":
        return tasks
    if export_kind == "confirmed":
        return [row for row in tasks if row["payload"].get("answer") == "accept"]
    if export_kind == "auto":
        return [row for row in tasks if row["payload"].get("meta", {}).get("route") == "auto_accept"]
    if export_kind == "reviewed":
        return [row for row in tasks if row["payload"].get("meta", {}).get("reviewed")]
    if export_kind == "hard":
        return [row for row in tasks if row["payload"].get("meta", {}).get("hard_example")]
    if export_kind == "low_confidence":
        return [row for row in tasks if row["payload"].get("meta", {}).get("route") == "review"]
    raise ValueError(f"unknown export kind: {export_kind}")


def build_dataset_stats(
    tasks: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    label_counter: Counter[str] = Counter()
    span_lengths: list[int] = []
    route_counter: Counter[str] = Counter()

    for row in tasks:
        payload = row["payload"]
        route = payload.get("meta", {}).get("route", "未路由")
        route_counter[route] += 1
        for span in payload.get("spans", []):
            label_counter[span.get("label", "未知")] += 1
            if span.get("start", -1) >= 0 and span.get("end", -1) > span.get("start", -1):
                span_lengths.append(int(span["end"]) - int(span["start"]))

    pending_reviews = [row for row in reviews if row["payload"].get("status") == "pending"]
    accepted_reviews = [row for row in reviews if row["payload"].get("status") == "accepted"]
    hard_examples = [row for row in tasks if row["payload"].get("meta", {}).get("hard_example")]
    manually_edited = [row for row in reviews if row["payload"].get("meta", {}).get("manually_edited")]
    promoted_to_gold = [row for row in tasks if row["payload"].get("meta", {}).get("promote_to_gold")]
    agreement_values = [
        float(row["payload"].get("meta", {}).get("agreement", 0.0))
        for row in tasks
        if "agreement" in row["payload"].get("meta", {})
    ]
    low_consistency = [value for value in agreement_values if value < 0.6]
    total_tasks = len(tasks)
    auto_count = route_counter.get("auto_accept", 0)
    review_count = route_counter.get("review", 0)

    return {
        "task_count": total_tasks,
        "prediction_count": len(predictions),
        "review_count": len(reviews),
        "pending_review_count": len(pending_reviews),
        "accepted_review_count": len(accepted_reviews),
        "job_count": len(jobs),
        "auto_accept_rate": round(auto_count / total_tasks, 4) if total_tasks else 0.0,
        "review_rate": round(review_count / total_tasks, 4) if total_tasks else 0.0,
        "hard_example_count": len(hard_examples),
        "manual_edit_count": len(manually_edited),
        "promoted_to_gold_count": len(promoted_to_gold),
        "avg_agreement": round(sum(agreement_values) / len(agreement_values), 4) if agreement_values else 0.0,
        "low_consistency_count": len(low_consistency),
        "label_distribution": dict(label_counter),
        "route_distribution": dict(route_counter),
        "avg_span_length": round(sum(span_lengths) / len(span_lengths), 2) if span_lengths else 0.0,
    }


def build_markdown_report(stats: dict[str, Any]) -> str:
    lines = [
        "# Rosetta 标注报告",
        "",
        f"- 任务总数: {stats['task_count']}",
        f"- 候选标注数: {stats['prediction_count']}",
        f"- 审核任务数: {stats['review_count']}",
        f"- 待审核数: {stats['pending_review_count']}",
        f"- 自动通过率: {stats['auto_accept_rate']}",
        f"- 人工审核率: {stats['review_rate']}",
        f"- 疑难样例数: {stats.get('hard_example_count', 0)}",
        f"- 人工修改数: {stats.get('manual_edit_count', 0)}",
        f"- 晋升为 gold-like 样例数: {stats.get('promoted_to_gold_count', 0)}",
        f"- 平均候选一致性: {stats.get('avg_agreement', 0.0)}",
        f"- 平均 span 长度: {stats['avg_span_length']}",
        "",
        "## 标签分布",
    ]
    for label, count in stats["label_distribution"].items():
        lines.append(f"- {label}: {count}")
    lines.extend(["", "## 路由分布"])
    for route, count in stats["route_distribution"].items():
        lines.append(f"- {route}: {count}")
    return "\n".join(lines) + "\n"


def build_experiment_report(
    stats: dict[str, Any],
    concept_versions: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
) -> str:
    lines = [build_markdown_report(stats).rstrip(), "", "## 概念自举版本"]
    if concept_versions:
        for row in sorted(concept_versions, key=lambda item: item["payload"].get("version", 0)):
            payload = row["payload"]
            metadata = payload.get("metadata", {})
            lines.append(
                "- "
                f"v{payload.get('version')}: pass={metadata.get('pass_count', '-')}, "
                f"failed={len(payload.get('failed_task_ids', []))}, "
                f"unstable={len(payload.get('unstable_task_ids', []))}, "
                f"round={metadata.get('round_index', '-')}"
            )
    else:
        lines.append("- 暂无概念版本记录")

    lines.extend(["", "## 主动审核反馈"])
    error_counter: Counter[str] = Counter()
    for row in reviews:
        error_type = row["payload"].get("meta", {}).get("error_type")
        if error_type:
            error_counter[str(error_type)] += 1
    if error_counter:
        for error_type, count in error_counter.items():
            lines.append(f"- {error_type}: {count}")
    else:
        lines.append("- 暂无错误类型记录")
    return "\n".join(lines) + "\n"
