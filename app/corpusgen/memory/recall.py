from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

import numpy as np

from app.corpusgen.contracts import CorpusSpec, MemoryRecord, RetrievalHit

Embedder = Callable[[CorpusSpec, list[str]], list[list[float]]]
_INDEX_CACHE: dict[str, tuple[list[str], np.ndarray]] = {}


def build_memory_index(
    spec: CorpusSpec,
    records: list[MemoryRecord],
    embedder: Embedder,
    force_rebuild: bool = False,
) -> dict:
    key = _index_key(spec, records)
    matrix_path, meta_path = _artifact_paths(spec, key)

    if force_rebuild:
        _INDEX_CACHE.pop(key, None)
        if matrix_path.exists():
            matrix_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

    if key in _INDEX_CACHE and not _dimension_matches(spec, _INDEX_CACHE[key][1].shape[1]):
        _INDEX_CACHE.pop(key, None)
        if matrix_path.exists():
            matrix_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

    existing_meta: dict[str, object] | None = None
    if meta_path.exists():
        existing_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if not _dimension_matches(spec, int(existing_meta.get("dimension", 0))):
            if matrix_path.exists():
                matrix_path.unlink()
            meta_path.unlink()
            existing_meta = None

    if not matrix_path.exists() or not meta_path.exists():
        vectors = embedder(spec, [_record_index_text(record) for record in records])
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] != len(records):
            raise ValueError("embedding 结果维度非法，无法构建 memory index")
        if not _dimension_matches(spec, int(matrix.shape[1])):
            raise ValueError(
                f"embedding 维度与 spec 不一致: expected={spec.embedding_dimensions}, actual={int(matrix.shape[1])}"
            )
        matrix = _normalize(matrix)
        np.save(matrix_path, matrix)
        meta_path.write_text(
            json.dumps(
                {
                    "chunk_ids": [record.chunk_id for record in records],
                    "dimension": int(matrix.shape[1]),
                    "record_count": len(records),
                    "embedding_model": spec.embedding_model,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        _INDEX_CACHE[key] = ([record.chunk_id for record in records], matrix)
    elif key not in _INDEX_CACHE:
        _INDEX_CACHE[key] = (
            existing_meta["chunk_ids"] if existing_meta is not None else json.loads(meta_path.read_text(encoding="utf-8"))["chunk_ids"],
            np.load(matrix_path).astype(np.float32),
        )

    chunk_ids, matrix = _INDEX_CACHE[key]
    return {
        "index_key": key,
        "matrix_path": str(matrix_path),
        "meta_path": str(meta_path),
        "record_count": len(chunk_ids),
        "dimension": int(matrix.shape[1]),
    }


def query_memory_index(
    spec: CorpusSpec,
    records: list[MemoryRecord],
    query_text: str,
    embedder: Embedder,
    top_k: int | None = None,
) -> list[RetrievalHit]:
    build_memory_index(spec, records, embedder=embedder)
    key = _index_key(spec, records)
    chunk_ids, matrix = _INDEX_CACHE[key]
    query_vector = np.asarray(embedder(spec, [query_text]), dtype=np.float32)
    query_vector = _normalize(query_vector)[0]

    scores = matrix @ query_vector
    limit = min(top_k or spec.max_context_chunks, len(chunk_ids))
    if limit == 0:
        return []

    top_indices = np.argpartition(-scores, kth=limit - 1)[:limit]
    ordered = top_indices[np.argsort(-scores[top_indices], kind="mergesort")]
    record_map = {record.chunk_id: record for record in records}
    return [
        RetrievalHit(record=record_map[chunk_ids[index]], score=float(scores[index]))
        for index in ordered
    ]


def _index_key(spec: CorpusSpec, records: list[MemoryRecord]) -> str:
    payload = json.dumps(
        {
            "name": spec.name,
            "embedding_model": spec.embedding_model,
            "embedding_dimensions": spec.embedding_dimensions,
            "records": [
                {
                    "chunk_id": record.chunk_id,
                    "summary": record.summary,
                    "canonical_points": list(record.canonical_points),
                    "terminology": list(record.terminology),
                }
                for record in records
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _artifact_paths(spec: CorpusSpec, key: str) -> tuple[Path, Path]:
    index_dir = Path(spec.index_dir) / spec.name
    index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir / f"{key}.npy", index_dir / f"{key}.json"


def _record_index_text(record: MemoryRecord) -> str:
    parts = [
        record.title,
        record.summary,
        *record.canonical_points,
        " ".join(record.terminology),
    ]
    return "\n".join(part for part in parts if part.strip())


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return matrix / norms


def _dimension_matches(spec: CorpusSpec, actual_dimension: int) -> bool:
    if spec.embedding_dimensions is None:
        return actual_dimension > 0
    return actual_dimension == spec.embedding_dimensions
