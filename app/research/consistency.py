from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations

from app.research.bootstrap_contracts import BootstrapCandidate, BootstrapSpan


@dataclass(frozen=True)
class ConsistencyScore:
    sample_id: str
    candidate_count: int
    pairwise_span_f1: float
    exact_match_rate: float
    average_model_confidence: float | None
    uncertainty_score: float
    route: str


def score_candidate_consistency(
    sample_id: str,
    candidates: list[BootstrapCandidate],
    high_threshold: float = 0.95,
    medium_threshold: float = 0.6,
) -> ConsistencyScore:
    sample_candidates = [candidate for candidate in candidates if candidate.sample_id == sample_id]
    if not sample_candidates:
        return ConsistencyScore(
            sample_id=sample_id,
            candidate_count=0,
            pairwise_span_f1=0.0,
            exact_match_rate=0.0,
            average_model_confidence=None,
            uncertainty_score=1.0,
            route="low",
        )

    pairwise_f1 = _pairwise_span_f1(sample_candidates)
    exact_rate = _exact_match_rate(sample_candidates)
    avg_confidence = _average_confidence(sample_candidates)
    uncertainty = _uncertainty_score(pairwise_f1, avg_confidence)
    route = _route(pairwise_f1, exact_rate, avg_confidence, high_threshold, medium_threshold)
    return ConsistencyScore(
        sample_id=sample_id,
        candidate_count=len(sample_candidates),
        pairwise_span_f1=pairwise_f1,
        exact_match_rate=exact_rate,
        average_model_confidence=avg_confidence,
        uncertainty_score=uncertainty,
        route=route,
    )


def score_candidate_groups(candidates: list[BootstrapCandidate]) -> list[ConsistencyScore]:
    sample_ids = sorted({candidate.sample_id for candidate in candidates})
    return [score_candidate_consistency(sample_id, candidates) for sample_id in sample_ids]


def consistency_score_to_dict(score: ConsistencyScore) -> dict:
    return asdict(score)


def span_f1(left: tuple[BootstrapSpan, ...], right: tuple[BootstrapSpan, ...]) -> float:
    left_keys = {_span_key(span) for span in left}
    right_keys = {_span_key(span) for span in right}
    if not left_keys and not right_keys:
        return 1.0
    if not left_keys or not right_keys:
        return 0.0

    overlap = len(left_keys & right_keys)
    precision = overlap / len(left_keys)
    recall = overlap / len(right_keys)
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


def _pairwise_span_f1(candidates: list[BootstrapCandidate]) -> float:
    if len(candidates) == 1:
        return 1.0
    scores = [
        span_f1(left.spans, right.spans)
        for left, right in combinations(candidates, 2)
    ]
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def _exact_match_rate(candidates: list[BootstrapCandidate]) -> float:
    if not candidates:
        return 0.0
    first = {_span_key(span) for span in candidates[0].spans}
    exact = sum(1 for candidate in candidates if {_span_key(span) for span in candidate.spans} == first)
    return round(exact / len(candidates), 4)


def _average_confidence(candidates: list[BootstrapCandidate]) -> float | None:
    values = [candidate.model_confidence for candidate in candidates if candidate.model_confidence is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _uncertainty_score(pairwise_f1: float, avg_confidence: float | None) -> float:
    disagreement = 1 - pairwise_f1
    confidence_penalty = 0.0 if avg_confidence is None else 1 - avg_confidence
    if avg_confidence is None:
        return round(disagreement, 4)
    return round((disagreement * 0.7) + (confidence_penalty * 0.3), 4)


def _route(
    pairwise_f1: float,
    exact_rate: float,
    avg_confidence: float | None,
    high_threshold: float,
    medium_threshold: float,
) -> str:
    confidence_ok = avg_confidence is None or avg_confidence >= 0.7
    if pairwise_f1 >= high_threshold and exact_rate >= 0.8 and confidence_ok:
        return "high"
    if pairwise_f1 >= medium_threshold:
        return "medium"
    return "low"


def _span_key(span: BootstrapSpan) -> tuple[int, int, str, str, bool]:
    return (span.start, span.end, span.text, span.label, span.implicit)
