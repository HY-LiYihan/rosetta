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
