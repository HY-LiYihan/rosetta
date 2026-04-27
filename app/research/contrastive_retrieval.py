from __future__ import annotations

import re
from dataclasses import dataclass

from app.research.bootstrap_contracts import BootstrapSample
from app.research.bootstrap_io import sample_to_dict

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


@dataclass(frozen=True)
class ContrastiveHit:
    role: str
    sample_id: str
    score: float
    sample: BootstrapSample


@dataclass(frozen=True)
class ContrastiveSelection:
    query_id: str
    similar: tuple[ContrastiveHit, ...]
    boundary: tuple[ContrastiveHit, ...]


def select_contrastive_examples(
    query: BootstrapSample,
    examples: list[BootstrapSample],
    similar_k: int = 3,
    boundary_k: int = 1,
) -> ContrastiveSelection:
    candidates = [example for example in examples if example.id != query.id]
    scored = [
        (example, lexical_similarity(query.text, example.text))
        for example in candidates
    ]

    similar = [
        ContrastiveHit(role="similar", sample_id=example.id, score=score, sample=example)
        for example, score in sorted(scored, key=lambda item: (-item[1], item[0].id))[: max(0, similar_k)]
    ]

    selected_ids = {hit.sample_id for hit in similar}
    boundary_pool = [(example, score) for example, score in scored if example.id not in selected_ids]
    boundary = [
        ContrastiveHit(role="boundary", sample_id=example.id, score=score, sample=example)
        for example, score in sorted(boundary_pool, key=lambda item: (item[1], item[0].id))[: max(0, boundary_k)]
    ]

    return ContrastiveSelection(query_id=query.id, similar=tuple(similar), boundary=tuple(boundary))


def contrastive_selection_to_dict(selection: ContrastiveSelection) -> dict:
    return {
        "query_id": selection.query_id,
        "similar": [_hit_to_dict(hit) for hit in selection.similar],
        "boundary": [_hit_to_dict(hit) for hit in selection.boundary],
    }


def lexical_similarity(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return round(overlap / union, 4) if union else 0.0


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def _hit_to_dict(hit: ContrastiveHit) -> dict:
    return {
        "role": hit.role,
        "sample_id": hit.sample_id,
        "score": hit.score,
        "sample": sample_to_dict(hit.sample),
    }
