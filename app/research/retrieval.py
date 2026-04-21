from __future__ import annotations

import re

from app.research.contracts import ResearchConfig, ResearchExample, ResearchSample

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


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


def select_examples(config: ResearchConfig, sample: ResearchSample) -> list[ResearchExample]:
    bank = list(config.example_bank)
    if not bank:
        return []

    if config.retrieval_strategy != "lexical":
        raise ValueError(f"不支持的检索策略: {config.retrieval_strategy}")

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

    # 保留至少一个 hard example，避免动态 few-shot 退化为纯典型例。
    if config.hard_examples and config.top_k_examples > 1 and not any(ex.example_type == "hard" for ex in selected):
        hard_candidate = max(
            config.hard_examples,
            key=lambda example: (_lexical_similarity(sample.text, example.text), example.id),
        )
        selected = selected[:-1] + [hard_candidate]

    deduped: list[ResearchExample] = []
    seen_ids: set[str] = set()
    for example in selected:
        if example.id in seen_ids:
            continue
        seen_ids.add(example.id)
        deduped.append(example)
    return deduped[: config.top_k_examples]
