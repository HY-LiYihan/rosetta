from __future__ import annotations

import re

from app.corpusgen.contracts import CorpusSpec, MemoryRecord, SeedChunk


def build_memory_records(spec: CorpusSpec, chunks: list[SeedChunk]) -> list[MemoryRecord]:
    records: list[MemoryRecord] = []
    for chunk in chunks:
        summary = shorten_text(chunk.text, spec.memory_summary_chars)
        canonical_points = tuple(_extract_sentences(chunk.text, limit=3, max_chars=140))
        terminology = tuple(_derive_terms(chunk))
        records.append(
            MemoryRecord(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                title=chunk.title,
                summary=summary,
                source_excerpt=shorten_text(chunk.text, spec.max_source_chars),
                canonical_points=canonical_points,
                terminology=terminology,
                language=chunk.language,
                domain=chunk.domain,
                tags=chunk.tags,
                metadata=chunk.metadata,
            )
        )
    return records


def memory_record_to_dict(record: MemoryRecord) -> dict:
    return {
        "chunk_id": record.chunk_id,
        "doc_id": record.doc_id,
        "title": record.title,
        "summary": record.summary,
        "source_excerpt": record.source_excerpt,
        "canonical_points": list(record.canonical_points),
        "terminology": list(record.terminology),
        "language": record.language,
        "domain": record.domain,
        "tags": list(record.tags),
        "metadata": record.metadata,
    }


def memory_record_from_dict(payload: dict) -> MemoryRecord:
    return MemoryRecord(
        chunk_id=str(payload["chunk_id"]),
        doc_id=str(payload["doc_id"]),
        title=str(payload.get("title", payload["doc_id"])),
        summary=str(payload.get("summary", "")),
        source_excerpt=str(payload.get("source_excerpt", "")),
        canonical_points=tuple(str(item) for item in payload.get("canonical_points", [])),
        terminology=tuple(str(item) for item in payload.get("terminology", [])),
        language=str(payload.get("language", "unknown")),
        domain=str(payload.get("domain", "general")),
        tags=tuple(str(item) for item in payload.get("tags", [])),
        metadata=dict(payload.get("metadata", {})),
    )


def shorten_text(text: str, max_chars: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    truncated = cleaned[: max_chars - 1].rstrip()
    return f"{truncated}…"


def _extract_sentences(text: str, limit: int, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[。！？!?；;])\s*", text.strip())
    results: list[str] = []
    for sentence in sentences:
        normalized = " ".join(sentence.split()).strip()
        if not normalized:
            continue
        results.append(shorten_text(normalized, max_chars))
        if len(results) >= limit:
            break
    if not results and text.strip():
        return [shorten_text(text.strip(), max_chars)]
    return results


def _derive_terms(chunk: SeedChunk) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()

    for item in chunk.tags:
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            terms.append(normalized)

    metadata_terms = chunk.metadata.get("keywords") or chunk.metadata.get("terminology") or []
    if isinstance(metadata_terms, list):
        for item in metadata_terms:
            normalized = str(item).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                terms.append(normalized)

    title = chunk.title.strip()
    if title and title not in seen and len(title) <= 36:
        terms.append(title)

    return terms[:12]
