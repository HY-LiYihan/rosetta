from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

import numpy as np

from app.research.contracts import ResearchConfig, ResearchExample

Embedder = Callable[[ResearchConfig, list[str]], list[list[float]]]
_INDEX_CACHE: dict[str, tuple[list[str], np.ndarray]] = {}


def _index_payload(config: ResearchConfig, examples: tuple[ResearchExample, ...]) -> dict:
    return {
        "config_name": config.name,
        "strategy": config.retrieval_strategy,
        "embedding_model": config.embedding_model,
        "embedding_dimensions": config.embedding_dimensions,
        "examples": [
            {
                "id": example.id,
                "text": example.text,
                "annotation": example.annotation,
                "explanation": example.explanation,
                "rationale": example.rationale,
                "example_type": example.example_type,
            }
            for example in examples
        ],
    }


def _index_key(config: ResearchConfig, examples: tuple[ResearchExample, ...]) -> str:
    payload = json.dumps(_index_payload(config, examples), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return matrix / norms


def _artifact_paths(config: ResearchConfig, key: str) -> tuple[Path, Path]:
    index_dir = Path(config.index_dir) / config.name
    index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir / f"{key}.npy", index_dir / f"{key}.json"


def _example_index_text(example: ResearchExample) -> str:
    chunks = [example.text, example.explanation]
    if example.rationale:
        chunks.append(example.rationale)
    return "\n".join(chunk for chunk in chunks if chunk.strip())


def build_example_index(
    config: ResearchConfig,
    embedder: Embedder,
    force_rebuild: bool = False,
) -> dict:
    if config.retrieval_strategy != "embedding":
        raise ValueError("只有 `embedding` 检索策略才需要构建向量索引")

    examples = config.example_bank
    key = _index_key(config, examples)
    matrix_path, meta_path = _artifact_paths(config, key)

    if force_rebuild:
        _INDEX_CACHE.pop(key, None)
        if matrix_path.exists():
            matrix_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

    if not matrix_path.exists() or not meta_path.exists():
        texts = [_example_index_text(example) for example in examples]
        vectors = embedder(config, texts)
        matrix = np.asarray(vectors, dtype=np.float32)
        matrix = _normalize(matrix)
        matrix_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(matrix_path, matrix)
        meta_path.write_text(
            json.dumps(
                {
                    "example_ids": [example.id for example in examples],
                    "dimension": int(matrix.shape[1]),
                    "example_count": len(examples),
                    "embedding_model": config.embedding_model,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        _INDEX_CACHE[key] = ([example.id for example in examples], matrix)
    else:
        if key not in _INDEX_CACHE:
            _INDEX_CACHE[key] = (
                json.loads(meta_path.read_text(encoding="utf-8"))["example_ids"],
                np.load(matrix_path).astype(np.float32),
            )

    ids, matrix = _INDEX_CACHE[key]
    return {
        "index_key": key,
        "matrix_path": str(matrix_path),
        "meta_path": str(meta_path),
        "example_count": len(ids),
        "dimension": int(matrix.shape[1]),
    }


def query_example_index(
    config: ResearchConfig,
    query_text: str,
    embedder: Embedder,
) -> list[tuple[str, float]]:
    build_example_index(config, embedder=embedder)
    key = _index_key(config, config.example_bank)
    ids, matrix = _INDEX_CACHE[key]
    query_vector = np.asarray(embedder(config, [query_text]), dtype=np.float32)
    query_vector = _normalize(query_vector)[0]

    scores = matrix @ query_vector
    top_k = min(config.top_k_examples, len(ids))
    if top_k == 0:
        return []
    top_indices = np.argpartition(-scores, kth=top_k - 1)[:top_k]
    ordered = top_indices[np.argsort(-scores[top_indices], kind="mergesort")]
    return [(ids[index], float(scores[index])) for index in ordered]
