from __future__ import annotations


def build_home_metrics(concepts: list[dict], annotation_history: list[dict]) -> dict:
    custom_count = len([c for c in concepts if not c.get("is_default", False)])
    history_count = len(annotation_history)
    avg_length = 0
    if annotation_history:
        avg_length = sum(len(h.get("annotation", "")) for h in annotation_history) / history_count

    return {
        "concept_count": len(concepts),
        "custom_count": custom_count,
        "history_count": history_count,
        "history_delta": "最近记录" if history_count else "暂无记录",
        "avg_length": avg_length,
    }
