from __future__ import annotations

from dataclasses import asdict, dataclass

from app.research.bootstrap_contracts import BootstrapCandidate
from app.research.bootstrap_io import candidate_to_dict
from app.research.consistency import ConsistencyScore

MANUAL_OPTION_ID = "__manual__"


@dataclass(frozen=True)
class ReviewOption:
    option_id: str
    candidate_id: str
    annotation_markup: str
    explanation: str
    model_confidence: float | None


@dataclass(frozen=True)
class HumanReviewTask:
    sample_id: str
    route: str
    priority: int
    prompt: str
    options: tuple[ReviewOption, ...]
    manual_option_id: str = MANUAL_OPTION_ID


def build_human_review_queue(
    candidates: list[BootstrapCandidate],
    scores: list[ConsistencyScore],
    include_routes: tuple[str, ...] = ("medium", "low"),
) -> list[HumanReviewTask]:
    candidate_map: dict[str, list[BootstrapCandidate]] = {}
    for candidate in candidates:
        candidate_map.setdefault(candidate.sample_id, []).append(candidate)

    tasks: list[HumanReviewTask] = []
    for score in scores:
        if score.route not in include_routes:
            continue
        sample_candidates = sorted(candidate_map.get(score.sample_id, []), key=lambda item: item.candidate_id)
        if not sample_candidates:
            continue
        tasks.append(_build_task(score, sample_candidates))

    return sorted(tasks, key=lambda task: (-task.priority, task.sample_id))


def human_review_task_to_dict(task: HumanReviewTask) -> dict:
    return {
        "sample_id": task.sample_id,
        "route": task.route,
        "priority": task.priority,
        "prompt": task.prompt,
        "manual_option_id": task.manual_option_id,
        "options": [asdict(option) for option in task.options],
    }


def candidate_bundle_for_review(candidates: list[BootstrapCandidate]) -> list[dict]:
    return [candidate_to_dict(candidate) for candidate in sorted(candidates, key=lambda item: item.candidate_id)]


def _build_task(score: ConsistencyScore, candidates: list[BootstrapCandidate]) -> HumanReviewTask:
    options = tuple(
        ReviewOption(
            option_id=chr(ord("A") + index),
            candidate_id=candidate.candidate_id,
            annotation_markup=candidate.annotation_markup,
            explanation=candidate.explanation,
            model_confidence=candidate.model_confidence,
        )
        for index, candidate in enumerate(candidates)
    )
    prompt = (
        "请选择最接近正确答案的候选；如果都不对，请选择手动修正。"
        f" 当前路由={score.route}, span-F1={score.pairwise_span_f1}, exact={score.exact_match_rate}."
    )
    return HumanReviewTask(
        sample_id=score.sample_id,
        route=score.route,
        priority=_priority(score.route, score.uncertainty_score),
        prompt=prompt,
        options=options,
    )


def _priority(route: str, uncertainty_score: float) -> int:
    base = {"low": 100, "medium": 50, "high": 10}.get(route, 0)
    return base + int(round(uncertainty_score * 10))
