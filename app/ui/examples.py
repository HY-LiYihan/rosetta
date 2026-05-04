from __future__ import annotations

from app.data.official_sample import (
    PROFESSIONAL_NER_EXAMPLE,
    professional_ner_gold_jsonl,
)

# Backward-compatible aliases for older tests, docs snippets, and CLI imports.
HARD_SCIENCE_TERM_EXAMPLE = PROFESSIONAL_NER_EXAMPLE


def hard_science_gold_jsonl() -> str:
    return professional_ner_gold_jsonl()
