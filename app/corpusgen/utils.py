from __future__ import annotations


def strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def dedupe_strings(items: list[str], limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for item in items:
        normalized = str(item).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            results.append(normalized)
            if limit is not None and len(results) >= limit:
                break
    return results
