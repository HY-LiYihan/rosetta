from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil


@dataclass(frozen=True)
class CorpusGenre:
    name: str
    weight: float
    instruction: str
    style: str
    difficulty: str = "mixed"


@dataclass(frozen=True)
class CompressionPolicy:
    brief_max_chars: int
    evidence_max_items: int
    term_max_items: int
    style_max_items: int
    failure_max_items: int


@dataclass(frozen=True)
class QualityPolicy:
    min_prompt_chars: int
    min_response_chars: int
    max_similarity: float
    require_term_overlap: bool


@dataclass(frozen=True)
class CorpusSpec:
    name: str
    description: str
    platform: str
    model: str
    api_key_env: str
    api_key_secret: str | None
    system_prompt: str
    embedding_model: str
    embedding_dimensions: int | None
    output_dir: str
    index_dir: str
    domain: str
    language: str
    target_schema: str
    total_samples: int
    samples_per_task: int
    seed_chunk_size: int
    seed_chunk_overlap: int
    memory_summary_chars: int
    max_context_chunks: int
    max_source_chars: int
    temperature: float
    genres: tuple[CorpusGenre, ...]
    style_requirements: tuple[str, ...]
    failure_modes: tuple[str, ...]
    banned_terms: tuple[str, ...]
    compression: CompressionPolicy
    quality: QualityPolicy

    @property
    def task_count(self) -> int:
        return ceil(self.total_samples / self.samples_per_task)


@dataclass(frozen=True)
class SeedDocument:
    doc_id: str
    title: str
    text: str
    source_type: str
    language: str
    domain: str
    tags: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SeedChunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    language: str
    domain: str
    tags: tuple[str, ...]
    order: int
    token_estimate: int
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryRecord:
    chunk_id: str
    doc_id: str
    title: str
    summary: str
    source_excerpt: str
    canonical_points: tuple[str, ...]
    terminology: tuple[str, ...]
    language: str
    domain: str
    tags: tuple[str, ...]
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalHit:
    record: MemoryRecord
    score: float


@dataclass(frozen=True)
class GenerationTask:
    task_id: str
    genre_name: str
    focus: str
    query: str
    instruction: str
    style: str
    difficulty: str
    target_count: int
    metadata: dict[str, object] = field(default_factory=dict)
