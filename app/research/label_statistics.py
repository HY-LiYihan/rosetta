from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from app.research.bootstrap_contracts import BootstrapSample, BootstrapSpan

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


@dataclass(frozen=True)
class TokenOccurrence:
    token: str
    start: int
    end: int


@dataclass(frozen=True)
class TokenLabelStat:
    token: str
    entity_count: int = 0
    context_count: int = 0
    other_count: int = 0

    @property
    def total(self) -> int:
        return self.entity_count + self.context_count + self.other_count

    @property
    def entity_probability(self) -> float:
        return _safe_ratio(self.entity_count, self.total)

    @property
    def context_probability(self) -> float:
        return _safe_ratio(self.context_count, self.total)

    @property
    def other_probability(self) -> float:
        return _safe_ratio(self.other_count, self.total)


def build_label_statistics(samples: list[BootstrapSample], context_window: int = 2) -> dict[str, TokenLabelStat]:
    counts: dict[str, dict[str, int]] = {}
    for sample in samples:
        tokens = tokenize_with_offsets(sample.text)
        entity_indices = _entity_token_indices(tokens, sample.spans)
        context_indices = _context_token_indices(tokens, entity_indices, context_window)
        for index, token in enumerate(tokens):
            bucket = _counts_for(counts, token.token)
            if index in entity_indices:
                bucket["entity_count"] += 1
            elif index in context_indices:
                bucket["context_count"] += 1
            else:
                bucket["other_count"] += 1

    return {
        token: TokenLabelStat(token=token, **values)
        for token, values in sorted(counts.items())
    }


def token_stat_to_dict(stat: TokenLabelStat) -> dict:
    row = asdict(stat)
    row["total"] = stat.total
    row["entity_probability"] = round(stat.entity_probability, 4)
    row["context_probability"] = round(stat.context_probability, 4)
    row["other_probability"] = round(stat.other_probability, 4)
    return row


def label_statistics_to_dict(stats: dict[str, TokenLabelStat]) -> dict:
    return {token: token_stat_to_dict(stat) for token, stat in stats.items()}


def tokenize_with_offsets(text: str) -> list[TokenOccurrence]:
    return [
        TokenOccurrence(token=match.group(0).lower(), start=match.start(), end=match.end())
        for match in TOKEN_PATTERN.finditer(text)
    ]


def token_overlaps_span(token: TokenOccurrence, span: BootstrapSpan) -> bool:
    if span.implicit:
        return False
    return token.start < span.end and token.end > span.start


def _entity_token_indices(tokens: list[TokenOccurrence], spans: tuple[BootstrapSpan, ...]) -> set[int]:
    return {
        index
        for index, token in enumerate(tokens)
        if any(token_overlaps_span(token, span) for span in spans)
    }


def _context_token_indices(tokens: list[TokenOccurrence], entity_indices: set[int], context_window: int) -> set[int]:
    context: set[int] = set()
    for index in entity_indices:
        for offset in range(1, context_window + 1):
            if index - offset >= 0:
                context.add(index - offset)
            if index + offset < len(tokens):
                context.add(index + offset)
    return context - entity_indices


def _counts_for(counts: dict[str, dict[str, int]], token: str) -> dict[str, int]:
    if token not in counts:
        counts[token] = {"entity_count": 0, "context_count": 0, "other_count": 0}
    return counts[token]


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator
