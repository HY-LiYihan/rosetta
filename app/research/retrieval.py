from __future__ import annotations

import re
from typing import Callable

from app.research.contracts import ResearchConfig, ResearchExample, ResearchSample
from app.research.indexing import query_example_index

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")
Embedder = Callable[[ResearchConfig, list[str]], list[list[float]]]


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def _lexical_similarity(left: str, right: str) -> float:
    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return intersection / union if union else 0.0


def _ensure_hard_example(
    config: ResearchConfig,
    selected: list[ResearchExample],
    sample_text: str,
) -> list[ResearchExample]:
    if not config.hard_examples or config.top_k_examples <= 1 or any(ex.example_type == "hard" for ex in selected):
        return selected

    hard_candidate = max(
        config.hard_examples,
        key=lambda example: (_lexical_similarity(sample_text, example.text), example.id),
    )
    trimmed = selected[:-1] if len(selected) >= config.top_k_examples else selected
    return trimmed + [hard_candidate]


def select_examples(
    config: ResearchConfig,
    sample: ResearchSample,
    embedder: Embedder | None = None,
) -> list[ResearchExample]:
    bank = list(config.example_bank)
    if not bank:
        return []

    if config.retrieval_strategy == "embedding":
        if embedder is None:
            raise ValueError("embedding 检索需要提供 embedder")
        score_pairs = query_example_index(config, sample.text, embedder=embedder)
        ranked_lookup = {example.id: example for example in bank}
        selected = [ranked_lookup[example_id] for example_id, _score in score_pairs if example_id in ranked_lookup]
        selected = _ensure_hard_example(config, selected, sample.text)
    elif config.retrieval_strategy == "lexical":
        ranked = sorted(
            bank,
            key=lambda example: (
                _lexical_similarity(sample.text, example.text),
                1 if example.example_type == "hard" else 0,
                example.id,
            ),
            reverse=True,
        )
        selected = ranked[: config.top_k_examples]
        selected = _ensure_hard_example(config, selected, sample.text)
    else:
        raise ValueError(f"不支持的检索策略: {config.retrieval_strategy}")

    deduped: list[ResearchExample] = []
    seen_ids: set[str] = set()
    for example in selected:
        if example.id in seen_ids:
            continue
        seen_ids.add(example.id)
        deduped.append(example)
    return deduped[: config.top_k_examples]
