from __future__ import annotations

from app.corpusgen.contracts import CorpusSpec, GenerationTask, RetrievalHit
from app.corpusgen.memory.layers import shorten_text


def build_context_pack(
    spec: CorpusSpec,
    task: GenerationTask,
    hits: list[RetrievalHit],
) -> dict:
    evidence_hits = hits[: spec.compression.evidence_max_items]
    term_pack = _collect_terms(task, evidence_hits, spec.compression.term_max_items)
    style_pack = _dedupe(
        [task.style, task.instruction, *spec.style_requirements],
        limit=spec.compression.style_max_items,
    )
    failure_pack = _dedupe(
        [
            *spec.failure_modes,
            *(f"避免使用禁用词：{term}" for term in spec.banned_terms),
        ],
        limit=spec.compression.failure_max_items,
    )

    evidence_pack = [
        {
            "chunk_id": hit.record.chunk_id,
            "score": round(hit.score, 4),
            "title": hit.record.title,
            "summary": hit.record.summary,
            "canonical_points": list(hit.record.canonical_points),
        }
        for hit in evidence_hits
    ]

    brief = shorten_text(
        (
            f"任务={task.genre_name}; 聚焦={task.focus}; 语言={spec.language}; "
            f"领域={spec.domain}; 风格={task.style}; 难度={task.difficulty}"
        ),
        spec.compression.brief_max_chars,
    )
    compressed_context = _format_context(
        brief=brief,
        evidence_pack=evidence_pack,
        term_pack=term_pack,
        style_pack=style_pack,
        failure_pack=failure_pack,
    )
    return {
        "task_brief": brief,
        "evidence_pack": evidence_pack,
        "term_pack": term_pack,
        "style_pack": style_pack,
        "failure_pack": failure_pack,
        "source_chunk_ids": [hit.record.chunk_id for hit in evidence_hits],
        "compressed_context": compressed_context,
    }


def _collect_terms(task: GenerationTask, hits: list[RetrievalHit], limit: int) -> list[str]:
    candidates = [task.focus]
    for hit in hits:
        candidates.extend(hit.record.terminology)
        candidates.extend(hit.record.tags)
    return _dedupe(candidates, limit=limit)


def _format_context(
    brief: str,
    evidence_pack: list[dict],
    term_pack: list[str],
    style_pack: list[str],
    failure_pack: list[str],
) -> str:
    lines = [
        "# Task Brief",
        brief,
        "",
        "# Evidence Pack",
    ]
    for item in evidence_pack:
        lines.append(f"- {item['chunk_id']} | {item['title']} | {item['summary']}")
        for point in item["canonical_points"][:2]:
            lines.append(f"  facts: {point}")
    lines.extend(
        [
            "",
            "# Term Pack",
            ", ".join(term_pack) if term_pack else "(empty)",
            "",
            "# Style Pack",
            "\n".join(f"- {item}" for item in style_pack) if style_pack else "- 保持自然、清晰、可复核",
            "",
            "# Failure Pack",
            "\n".join(f"- {item}" for item in failure_pack) if failure_pack else "- 不要脱离给定证据",
        ]
    )
    return "\n".join(lines)


def _dedupe(items: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for item in items:
        normalized = str(item).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            results.append(normalized)
        if len(results) >= limit:
            break
    return results
