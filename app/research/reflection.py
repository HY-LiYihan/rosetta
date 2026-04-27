from __future__ import annotations

from dataclasses import asdict, dataclass

from app.research.bootstrap_contracts import BootstrapCandidate, BootstrapSample
from app.research.label_statistics import TokenLabelStat, tokenize_with_offsets, token_overlaps_span


@dataclass(frozen=True)
class ReflectionItem:
    item_type: str
    token: str
    start: int
    end: int
    reason: str


@dataclass(frozen=True)
class ReflectionPlan:
    sample_id: str
    candidate_id: str
    items: tuple[ReflectionItem, ...]


def build_reflection_plan(
    sample: BootstrapSample,
    candidate: BootstrapCandidate,
    stats: dict[str, TokenLabelStat],
    entity_threshold: float = 0.6,
    max_items: int = 8,
) -> ReflectionPlan:
    tokens = tokenize_with_offsets(sample.text)
    predicted_spans = candidate.spans
    predicted_token_indices = {
        index
        for index, token in enumerate(tokens)
        if any(token_overlaps_span(token, span) for span in predicted_spans)
    }

    items: list[ReflectionItem] = []
    for index, token in enumerate(tokens):
        stat = stats.get(token.token)
        if stat is None and index not in predicted_token_indices:
            items.append(
                ReflectionItem(
                    item_type="unseen_token",
                    token=token.token,
                    start=token.start,
                    end=token.end,
                    reason="token 未出现在 gold/high-confidence 样本统计中，且当前未被标注",
                )
            )
        elif stat is not None and index not in predicted_token_indices and stat.entity_probability >= entity_threshold:
            items.append(
                ReflectionItem(
                    item_type="possible_false_negative",
                    token=token.token,
                    start=token.start,
                    end=token.end,
                    reason=f"历史统计中 entity_probability={stat.entity_probability:.2f}，但当前未标注",
                )
            )

    for span in predicted_spans:
        if span.implicit:
            continue
        edge_tokens = [token for token in tokens if token_overlaps_span(token, span)]
        for token in edge_tokens[:1] + edge_tokens[-1:]:
            stat = stats.get(token.token)
            if stat is not None and stat.context_probability > stat.entity_probability:
                items.append(
                    ReflectionItem(
                        item_type="boundary_token",
                        token=token.token,
                        start=token.start,
                        end=token.end,
                        reason=(
                            f"token 在历史统计中更常作为 context "
                            f"({stat.context_probability:.2f}) 而非 entity ({stat.entity_probability:.2f})"
                        ),
                    )
                )

    deduped: list[ReflectionItem] = []
    seen = set()
    for item in items:
        key = (item.item_type, item.start, item.end, item.token)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_items:
            break

    return ReflectionPlan(sample_id=sample.id, candidate_id=candidate.candidate_id, items=tuple(deduped))


def reflection_plan_to_dict(plan: ReflectionPlan) -> dict:
    return {
        "sample_id": plan.sample_id,
        "candidate_id": plan.candidate_id,
        "items": [asdict(item) for item in plan.items],
    }
