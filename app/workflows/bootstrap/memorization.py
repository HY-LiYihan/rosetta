from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from app.core.models import utc_timestamp
from app.runtime.store import RuntimeStore


COMMON_TOKENS = {
    "about",
    "after",
    "also",
    "annotation",
    "answer",
    "before",
    "candidate",
    "concept",
    "description",
    "example",
    "examples",
    "format",
    "from",
    "gold",
    "label",
    "labels",
    "mark",
    "model",
    "output",
    "prompt",
    "rule",
    "rules",
    "span",
    "spans",
    "task",
    "term",
    "terms",
    "text",
    "that",
    "this",
    "with",
}


@dataclass(frozen=True)
class CorpusFingerprint:
    source_ids: tuple[str, ...]
    token_hashes: tuple[str, ...]
    token_count: int
    normalization: str = "lowercase_word_tokens_and_cjk_grams_v1"
    created_at: str = field(default_factory=utc_timestamp)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_ids": self.source_ids,
            "token_hashes": self.token_hashes,
            "token_count": self.token_count,
            "normalization": self.normalization,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class LeakageCheckResult:
    passed: bool
    match_count: int
    matched_hashes: tuple[str, ...] = ()
    severity: str = "clean"
    field: str = ""
    reason: str = ""
    blocked: bool = False
    private_matches: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "match_count": self.match_count,
            "matched_hashes": self.matched_hashes,
            "severity": self.severity,
            "field": self.field,
            "reason": self.reason,
            "blocked": self.blocked,
        }


class MemorizationGuard:
    def __init__(
        self,
        fingerprint: CorpusFingerprint,
        allowed_terms: Iterable[str] = (),
        private_units_by_hash: dict[str, set[str]] | None = None,
        source_types_by_hash: dict[str, set[str]] | None = None,
    ):
        self.fingerprint = fingerprint
        self.allowed_terms = tuple(allowed_terms)
        self.allowed_hashes = frozenset(_hash_token(token) for token in _candidate_units(" ".join(self.allowed_terms)))
        self.blocked_hashes = frozenset(fingerprint.token_hashes) - self.allowed_hashes
        self.private_units_by_hash = private_units_by_hash or {}
        self.source_types_by_hash = source_types_by_hash or {}

    @classmethod
    def from_store(
        cls,
        store: RuntimeStore,
        task_ids: list[str],
        allowed_terms: Iterable[str] = (),
    ) -> "MemorizationGuard":
        source_texts: list[tuple[str, str]] = []
        source_ids: list[str] = []
        for task_id in task_ids:
            row = store.get_task(task_id)
            if row is None:
                continue
            payload = row["payload"]
            source_ids.append(task_id)
            source_texts.append((str(payload.get("text", "")), "source_text"))
            source_texts.append((str(payload.get("meta", {}).get("runtime_annotation", "")), "runtime_annotation"))
            source_texts.extend((str(span.get("text", "")), "gold_span") for span in payload.get("spans", []))
        fingerprint, private_units, source_types = _fingerprint(source_ids, source_texts)
        return cls(fingerprint, allowed_terms=allowed_terms, private_units_by_hash=private_units, source_types_by_hash=source_types)

    def with_validation_result(self, validation_result: dict) -> "MemorizationGuard":
        source_texts: list[tuple[str, str]] = []
        for detail in validation_result.get("details", []):
            source_texts.extend((str(span.get("text", "")), "model_span") for span in detail.get("predicted_spans", []))
        if not source_texts:
            return self
        _fingerprint_extra, private_units, source_types = _fingerprint(list(self.fingerprint.source_ids), source_texts)
        merged_hashes = set(self.fingerprint.token_hashes)
        merged_hashes.update(private_units)
        merged_private_units = {key: set(value) for key, value in self.private_units_by_hash.items()}
        for key, value in private_units.items():
            merged_private_units.setdefault(key, set()).update(value)
        merged_source_types = {key: set(value) for key, value in self.source_types_by_hash.items()}
        for key, value in source_types.items():
            merged_source_types.setdefault(key, set()).update(value)
        fingerprint = CorpusFingerprint(
            source_ids=self.fingerprint.source_ids,
            token_hashes=tuple(sorted(merged_hashes)),
            token_count=len(merged_hashes),
            normalization=self.fingerprint.normalization,
            created_at=self.fingerprint.created_at,
        )
        return MemorizationGuard(
            fingerprint,
            allowed_terms=self.allowed_terms,
            private_units_by_hash=merged_private_units,
            source_types_by_hash=merged_source_types,
        )

    def check(self, text: str, field: str = "") -> LeakageCheckResult:
        candidate_hashes = {_hash_token(unit) for unit in _candidate_units(text)}
        matched = tuple(sorted(candidate_hashes & self.blocked_hashes))
        passed = not matched
        source_types = {source_type for token_hash in matched for source_type in self.source_types_by_hash.get(token_hash, set())}
        severity = (
            "clean"
            if passed
            else "critical_leak"
            if source_types & {"gold_span", "runtime_annotation", "model_span"}
            else "soft_leak"
        )
        return LeakageCheckResult(
            passed=passed,
            match_count=len(matched),
            matched_hashes=matched[:20],
            severity=severity,
            field=field,
            reason="" if passed else "candidate_copies_corpus_or_answer_fragment",
            blocked=not passed,
            private_matches=tuple(sorted({unit for token_hash in matched for unit in self.private_units_by_hash.get(token_hash, set())}))[:20],
        )

    def summary(self) -> dict[str, Any]:
        return {
            "normalization": self.fingerprint.normalization,
            "source_count": len(self.fingerprint.source_ids),
            "token_count": self.fingerprint.token_count,
            "blocked_hash_count": len(self.blocked_hashes),
        }


def _fingerprint(source_ids: list[str], source_texts: list[tuple[str, str]]) -> tuple[CorpusFingerprint, dict[str, set[str]], dict[str, set[str]]]:
    private_units_by_hash: dict[str, set[str]] = {}
    source_types_by_hash: dict[str, set[str]] = {}
    for text, source_type in source_texts:
        for unit in _candidate_units(text):
            token_hash = _hash_token(unit)
            private_units_by_hash.setdefault(token_hash, set()).add(unit)
            source_types_by_hash.setdefault(token_hash, set()).add(source_type)
    hashes = tuple(sorted(private_units_by_hash))
    return (
        CorpusFingerprint(source_ids=tuple(source_ids), token_hashes=hashes, token_count=len(hashes)),
        private_units_by_hash,
        source_types_by_hash,
    )


def _candidate_units(text: str) -> list[str]:
    units: list[str] = []
    normalized = str(text or "").lower()
    words = re.findall(r"[a-z][a-z0-9-]*", normalized)
    filtered_words = [word for word in words if _keep_word(word)]
    units.extend(filtered_words)
    for size in (2, 3):
        units.extend(" ".join(filtered_words[index : index + size]) for index in range(0, max(0, len(filtered_words) - size + 1)))
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]+", normalized)
    for chunk in cjk_chunks:
        for size in (2, 3):
            units.extend(chunk[index : index + size] for index in range(0, max(0, len(chunk) - size + 1)))
    return [unit for unit in units if unit and unit not in COMMON_TOKENS]


def _keep_word(word: str) -> bool:
    return len(word) >= 4 and word not in COMMON_TOKENS and not word.isdigit()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
