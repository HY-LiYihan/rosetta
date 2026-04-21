from __future__ import annotations

import json
from pathlib import Path

from app.corpusgen.contracts import SeedChunk, SeedDocument


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def load_seed_documents(path: str | Path) -> list[SeedDocument]:
    dataset_path = Path(path)
    rows = _read_jsonl(dataset_path)
    return [_parse_seed_document(row, index) for index, row in enumerate(rows, start=1)]


def _parse_seed_document(payload: dict, index: int) -> SeedDocument:
    if not isinstance(payload, dict):
        raise ValueError(f"seed line {index}: 文档必须是对象")

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"seed line {index}: `text` 必须是非空字符串")

    doc_id = payload.get("id")
    if not isinstance(doc_id, str) or not doc_id.strip():
        doc_id = f"seed-{index:04d}"

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        title = doc_id

    tags = payload.get("tags", [])
    if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
        raise ValueError(f"seed line {index}: `tags` 必须是字符串列表")

    metadata = payload.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError(f"seed line {index}: `metadata` 必须是对象")

    return SeedDocument(
        doc_id=doc_id.strip(),
        title=title.strip(),
        text=text.strip(),
        source_type=str(payload.get("source_type", "reference")).strip() or "reference",
        language=str(payload.get("language", "unknown")).strip() or "unknown",
        domain=str(payload.get("domain", "general")).strip() or "general",
        tags=tuple(tag.strip() for tag in tags),
        metadata=metadata,
    )


def chunk_seed_documents(
    documents: list[SeedDocument],
    chunk_size: int,
    chunk_overlap: int,
) -> list[SeedChunk]:
    chunks: list[SeedChunk] = []
    for document in documents:
        pieces = _chunk_text(document.text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for order, piece in enumerate(pieces, start=1):
            chunks.append(
                SeedChunk(
                    chunk_id=f"{document.doc_id}-chunk-{order:03d}",
                    doc_id=document.doc_id,
                    title=document.title,
                    text=piece,
                    language=document.language,
                    domain=document.domain,
                    tags=document.tags,
                    order=order,
                    token_estimate=max(1, len(piece) // 4),
                    metadata=document.metadata,
                )
            )
    return chunks


def seed_chunk_to_dict(chunk: SeedChunk) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "doc_id": chunk.doc_id,
        "title": chunk.title,
        "text": chunk.text,
        "language": chunk.language,
        "domain": chunk.domain,
        "tags": list(chunk.tags),
        "order": chunk.order,
        "token_estimate": chunk.token_estimate,
        "metadata": chunk.metadata,
    }


def seed_chunk_from_dict(payload: dict) -> SeedChunk:
    return SeedChunk(
        chunk_id=str(payload["chunk_id"]),
        doc_id=str(payload["doc_id"]),
        title=str(payload.get("title", payload["doc_id"])),
        text=str(payload["text"]),
        language=str(payload.get("language", "unknown")),
        domain=str(payload.get("domain", "general")),
        tags=tuple(str(item) for item in payload.get("tags", [])),
        order=int(payload.get("order", 1)),
        token_estimate=int(payload.get("token_estimate", max(1, len(str(payload["text"])) // 4))),
        metadata=dict(payload.get("metadata", {})),
    )


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    cleaned = text.strip()
    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    boundary_chars = "。！？!?；;\n"
    min_window = max(80, chunk_size // 2)

    while start < len(cleaned):
        if len(cleaned) - start <= chunk_size:
            chunk = cleaned[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        rough_end = min(len(cleaned), start + chunk_size)
        boundary_end = rough_end
        for cursor in range(rough_end, max(start + min_window, start + 1), -1):
            if cleaned[cursor - 1] in boundary_chars:
                boundary_end = cursor
                break

        if boundary_end <= start:
            boundary_end = rough_end

        chunk = cleaned[start:boundary_end].strip()
        if chunk:
            chunks.append(chunk)

        next_start = max(boundary_end - chunk_overlap, start + 1)
        if next_start <= start:
            next_start = start + chunk_size
        start = next_start
    return chunks
