from __future__ import annotations

import json
from pathlib import Path

from app.corpusgen.contracts import CompressionPolicy, CorpusGenre, CorpusSpec, QualityPolicy

DEFAULT_SYSTEM_PROMPT = (
    "你是一个严格受控的科研语料生成助手。你只能基于提供的压缩上下文生成 JSON，"
    "不得编造与上下文冲突的事实，不得输出 JSON 以外的文本。"
)


class CorpusSpecError(ValueError):
    """Raised when a corpus generation spec is invalid."""


def _require_str(payload: dict, field: str, source: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CorpusSpecError(f"{source}: `{field}` 必须是非空字符串")
    return value.strip()


def _read_str_list(payload: dict, field: str, source: str) -> tuple[str, ...]:
    value = payload.get(field, [])
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise CorpusSpecError(f"{source}: `{field}` 必须是字符串列表")
    return tuple(item.strip() for item in value)


def _parse_genre(payload: dict, index: int) -> CorpusGenre:
    source = f"genres[{index}]"
    if not isinstance(payload, dict):
        raise CorpusSpecError(f"{source}: genre 必须是对象")

    weight = float(payload.get("weight", 1.0))
    if weight <= 0:
        raise CorpusSpecError(f"{source}: `weight` 必须大于 0")

    return CorpusGenre(
        name=_require_str(payload, "name", source),
        weight=weight,
        instruction=_require_str(payload, "instruction", source),
        style=_require_str(payload, "style", source),
        difficulty=str(payload.get("difficulty", "mixed")).strip() or "mixed",
    )


def parse_corpus_spec(payload: dict, source: str = "<memory>") -> CorpusSpec:
    if not isinstance(payload, dict):
        raise CorpusSpecError(f"{source}: 顶层必须是 JSON 对象")

    genres = tuple(_parse_genre(item, index) for index, item in enumerate(payload.get("genres", [])))
    if not genres:
        raise CorpusSpecError(f"{source}: 至少需要一个 genre")

    target_schema = str(payload.get("target_schema", "qa")).strip().lower()
    if target_schema not in {"qa", "instruction_response"}:
        raise CorpusSpecError(f"{source}: `target_schema` 只能是 `qa` 或 `instruction_response`")

    total_samples = int(payload.get("total_samples", 8))
    samples_per_task = int(payload.get("samples_per_task", 2))
    seed_chunk_size = int(payload.get("seed_chunk_size", 600))
    seed_chunk_overlap = int(payload.get("seed_chunk_overlap", 80))
    memory_summary_chars = int(payload.get("memory_summary_chars", 260))
    max_context_chunks = int(payload.get("max_context_chunks", 4))
    max_source_chars = int(payload.get("max_source_chars", 1600))

    integer_fields = {
        "total_samples": total_samples,
        "samples_per_task": samples_per_task,
        "seed_chunk_size": seed_chunk_size,
        "seed_chunk_overlap": seed_chunk_overlap,
        "memory_summary_chars": memory_summary_chars,
        "max_context_chunks": max_context_chunks,
        "max_source_chars": max_source_chars,
    }
    for field, value in integer_fields.items():
        if value < 1:
            raise CorpusSpecError(f"{source}: `{field}` 必须 >= 1")

    if seed_chunk_overlap >= seed_chunk_size:
        raise CorpusSpecError(f"{source}: `seed_chunk_overlap` 必须小于 `seed_chunk_size`")

    embedding_dimensions = payload.get("embedding_dimensions")
    if embedding_dimensions is not None:
        embedding_dimensions = int(embedding_dimensions)
        if embedding_dimensions < 1:
            raise CorpusSpecError(f"{source}: `embedding_dimensions` 必须 > 0")

    compression_payload = payload.get("compression", {})
    if not isinstance(compression_payload, dict):
        raise CorpusSpecError(f"{source}: `compression` 必须是对象")
    compression = CompressionPolicy(
        brief_max_chars=int(compression_payload.get("brief_max_chars", 420)),
        evidence_max_items=int(compression_payload.get("evidence_max_items", 4)),
        term_max_items=int(compression_payload.get("term_max_items", 10)),
        style_max_items=int(compression_payload.get("style_max_items", 6)),
        failure_max_items=int(compression_payload.get("failure_max_items", 6)),
    )

    quality_payload = payload.get("quality_filters", {})
    if not isinstance(quality_payload, dict):
        raise CorpusSpecError(f"{source}: `quality_filters` 必须是对象")
    quality = QualityPolicy(
        min_prompt_chars=int(quality_payload.get("min_prompt_chars", 12)),
        min_response_chars=int(quality_payload.get("min_response_chars", 48)),
        max_similarity=float(quality_payload.get("max_similarity", 0.92)),
        require_term_overlap=bool(quality_payload.get("require_term_overlap", True)),
    )

    return CorpusSpec(
        name=_require_str(payload, "name", source),
        description=str(payload.get("description", "")).strip(),
        platform=_require_str(payload, "platform", source),
        model=_require_str(payload, "model", source),
        api_key_env=_require_str(payload, "api_key_env", source),
        api_key_secret=str(payload.get("api_key_secret", "")).strip() or None,
        system_prompt=str(payload.get("system_prompt", DEFAULT_SYSTEM_PROMPT)).strip() or DEFAULT_SYSTEM_PROMPT,
        embedding_model=_require_str(payload, "embedding_model", source),
        embedding_dimensions=embedding_dimensions,
        output_dir=str(payload.get("output_dir", ".runtime/corpusgen")).strip() or ".runtime/corpusgen",
        index_dir=str(payload.get("index_dir", ".runtime/corpusgen/indexes")).strip() or ".runtime/corpusgen/indexes",
        domain=_require_str(payload, "domain", source),
        language=_require_str(payload, "language", source),
        target_schema=target_schema,
        total_samples=total_samples,
        samples_per_task=samples_per_task,
        seed_chunk_size=seed_chunk_size,
        seed_chunk_overlap=seed_chunk_overlap,
        memory_summary_chars=memory_summary_chars,
        max_context_chunks=max_context_chunks,
        max_source_chars=max_source_chars,
        temperature=float(payload.get("temperature", 0.5)),
        genres=genres,
        style_requirements=_read_str_list(payload, "style_requirements", source),
        failure_modes=_read_str_list(payload, "failure_modes", source),
        banned_terms=_read_str_list(payload, "banned_terms", source),
        compression=compression,
        quality=quality,
    )


def load_corpus_spec(path: str | Path) -> CorpusSpec:
    spec_path = Path(path)
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    return parse_corpus_spec(payload, source=str(spec_path))
