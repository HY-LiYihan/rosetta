from __future__ import annotations

from collections import Counter

from app.research.consistency import ConsistencyScore
from app.research.human_review import HumanReviewTask
from app.research.label_statistics import TokenLabelStat
from app.research.reflection import ReflectionPlan


def build_bootstrap_report(
    manifest: dict,
    scores: list[ConsistencyScore],
    review_queue: list[HumanReviewTask],
    label_stats: dict[str, TokenLabelStat],
    reflection_plans: list[ReflectionPlan],
    experiment: dict | None = None,
) -> str:
    route_counts = Counter(score.route for score in scores)
    reflection_counts = Counter(item.item_type for plan in reflection_plans for item in plan.items)
    top_entity_tokens = sorted(
        label_stats.values(),
        key=lambda stat: (stat.entity_count, stat.entity_probability, stat.token),
        reverse=True,
    )[:10]

    lines = [
        "# Concept Bootstrap Report",
        "",
        "## Summary",
        "",
        f"- Run name: `{manifest['run_name']}`",
        f"- Samples: {manifest['sample_count']}",
        f"- Candidate runs: {manifest['candidate_count']}",
        f"- Review tasks: {manifest['review_task_count']}",
        f"- Reflection plans: {manifest['reflection_plan_count']}",
        "",
    ]

    if experiment:
        dataset = experiment.get("dataset", {})
        lines.extend(
            [
                "## Experiment",
                "",
                f"- Name: `{experiment.get('name', manifest['run_name'])}`",
                f"- Dataset: {dataset.get('source', 'unknown')}",
                f"- Language: {dataset.get('language', 'unknown')}",
                f"- Domain: {dataset.get('domain', 'unknown')}",
                f"- Task: {dataset.get('task', 'unknown')}",
                "",
            ]
        )

    lines.extend(
        [
            "## Consistency Routes",
            "",
            "| route | count |",
            "| --- | ---: |",
        ]
    )
    for route in ("high", "medium", "low"):
        lines.append(f"| {route} | {route_counts.get(route, 0)} |")

    lines.extend(
        [
            "",
            "## Human Review",
            "",
            f"- Queue size: {len(review_queue)}",
            "- Policy: review `medium` and `low` routes first; sample `high` for audit.",
            "",
            "## Top Entity Tokens",
            "",
            "| token | entity_count | entity_prob | context_prob | other_prob |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for stat in top_entity_tokens:
        lines.append(
            f"| {stat.token} | {stat.entity_count} | {stat.entity_probability:.2f} | "
            f"{stat.context_probability:.2f} | {stat.other_probability:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Reflection Items",
            "",
            "| type | count |",
            "| --- | ---: |",
        ]
    )
    for item_type, count in sorted(reflection_counts.items()):
        lines.append(f"| {item_type} | {count} |")

    if experiment:
        baselines = experiment.get("baselines", [])
        metrics = experiment.get("metrics", [])
        lines.extend(
            [
                "",
                "## Planned Baselines",
                "",
                *(f"- `{baseline}`" for baseline in baselines),
                "",
                "## Planned Metrics",
                "",
                *(f"- `{metric}`" for metric in metrics),
            ]
        )

    lines.append("")
    return "\n".join(lines)
