from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np

WORD_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


@dataclass(frozen=True)
class LocalEmbeddingProfile:
    """Small deterministic embedding profile for local retrieval.

    This is intentionally dependency-light: it uses feature hashing over word
    and character n-grams, then L2-normalizes the vector. It is not a
    transformer-quality semantic model, but it avoids API calls, token cost,
    and exact token-overlap ranking.
    """

    model_id: str = "rosetta-local-hash-384"
    dimensions: int = 384
    word_ngrams: tuple[int, ...] = (1, 2)
    char_ngrams: tuple[int, ...] = (3, 4, 5)
    lowercase: bool = True
    word_weight: float = 1.0
    char_weight: float = 0.55
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "LocalEmbeddingProfile":
        dimensions = max(32, min(int(self.dimensions), 4096))
        word_ngrams = tuple(sorted({max(1, int(value)) for value in self.word_ngrams or (1,)}))
        char_ngrams = tuple(sorted({max(1, int(value)) for value in self.char_ngrams or (3,)}))
        return LocalEmbeddingProfile(
            model_id=self.model_id or "rosetta-local-hash-384",
            dimensions=dimensions,
            word_ngrams=word_ngrams,
            char_ngrams=char_ngrams,
            lowercase=bool(self.lowercase),
            word_weight=float(self.word_weight),
            char_weight=float(self.char_weight),
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True)
class EmbeddingHit:
    id: str
    text: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


class LocalHashingEmbedder:
    """OpenWebUI-style local embedding fallback without model downloads."""

    def __init__(self, profile: LocalEmbeddingProfile | None = None):
        self.profile = (profile or LocalEmbeddingProfile()).normalized()

    def embed(self, text: str) -> np.ndarray:
        return self.embed_many([text])[0]

    def embed_many(self, texts: Iterable[str]) -> np.ndarray:
        rows = [self._embed_one(str(text or "")) for text in texts]
        if not rows:
            return np.zeros((0, self.profile.dimensions), dtype=np.float32)
        matrix = np.vstack(rows).astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return matrix / norms

    def _embed_one(self, text: str) -> np.ndarray:
        vector = np.zeros(self.profile.dimensions, dtype=np.float32)
        normalized = text.lower() if self.profile.lowercase else text
        tokens = WORD_PATTERN.findall(normalized)
        for feature in _word_ngram_features(tokens, self.profile.word_ngrams):
            _add_feature(vector, f"w:{feature}", self.profile.word_weight)
        compact = re.sub(r"\s+", " ", normalized).strip()
        for feature in _char_ngram_features(compact, self.profile.char_ngrams):
            _add_feature(vector, f"c:{feature}", self.profile.char_weight)
        return vector


class LocalEmbeddingRetriever:
    def __init__(self, embedder: LocalHashingEmbedder | None = None):
        self.embedder = embedder or LocalHashingEmbedder()

    def search(
        self,
        query: str,
        documents: Iterable[dict[str, Any]],
        top_k: int,
        exclude_ids: set[str] | None = None,
    ) -> list[EmbeddingHit]:
        hits = rank_texts(query, documents, self.embedder, exclude_ids=exclude_ids)
        return hits[: max(0, int(top_k))]


def rank_texts(
    query: str,
    documents: Iterable[dict[str, Any]],
    embedder: LocalHashingEmbedder | None = None,
    exclude_ids: set[str] | None = None,
) -> list[EmbeddingHit]:
    embedder = embedder or LocalHashingEmbedder()
    rows = [dict(document) for document in documents if str(document.get("id", "")) not in (exclude_ids or set())]
    if not rows:
        return []
    texts = [str(row.get("text", "")) for row in rows]
    query_vector = embedder.embed(str(query or ""))
    matrix = embedder.embed_many(texts)
    scores = matrix @ query_vector
    hits = [
        EmbeddingHit(
            id=str(row.get("id", "")),
            text=str(row.get("text", "")),
            score=round(float(score), 4),
            payload=row,
        )
        for row, score in zip(rows, scores, strict=False)
    ]
    return sorted(hits, key=lambda hit: (-hit.score, hit.id))


def embedding_similarity(left: str, right: str, embedder: LocalHashingEmbedder | None = None) -> float:
    embedder = embedder or LocalHashingEmbedder()
    vectors = embedder.embed_many([left, right])
    if vectors.shape[0] != 2:
        return 0.0
    return round(float(vectors[0] @ vectors[1]), 4)


def _word_ngram_features(tokens: list[str], ns: tuple[int, ...]) -> Iterable[str]:
    for n in ns:
        if len(tokens) < n:
            continue
        for index in range(0, len(tokens) - n + 1):
            yield " ".join(tokens[index : index + n])


def _char_ngram_features(text: str, ns: tuple[int, ...]) -> Iterable[str]:
    if not text:
        return
    padded = f" {text} "
    for n in ns:
        if len(padded) < n:
            continue
        for index in range(0, len(padded) - n + 1):
            yield padded[index : index + n]


def _add_feature(vector: np.ndarray, feature: str, weight: float) -> None:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    raw = int.from_bytes(digest, byteorder="big", signed=False)
    index = raw % vector.shape[0]
    sign = 1.0 if ((raw >> 63) & 1) == 0 else -1.0
    vector[index] += sign * float(weight)
