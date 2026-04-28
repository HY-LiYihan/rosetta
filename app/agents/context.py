from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextChunk:
    id: str
    text: str
    source: str = ""
    score: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextPack:
    goal: str
    chunks: tuple[ContextChunk, ...]
    summary: str = ""
    budget_chars: int = 8000

    @property
    def text(self) -> str:
        sections: list[str] = []
        if self.summary:
            sections.append(f"[summary]\n{self.summary}")
        for chunk in self.chunks:
            source = f" ({chunk.source})" if chunk.source else ""
            sections.append(f"[{chunk.id}{source}]\n{chunk.text}")
        return "\n\n".join(sections)


class ContextEngine:
    def __init__(self, budget_chars: int = 8000, fresh_tail_chars: int = 2000):
        if budget_chars <= 0:
            raise ValueError("budget_chars must be positive")
        self.budget_chars = budget_chars
        self.fresh_tail_chars = fresh_tail_chars

    def build_pack(
        self,
        goal: str,
        fresh_text: str = "",
        retrieved: list[ContextChunk] | None = None,
        summaries: list[str] | None = None,
    ) -> ContextPack:
        remaining = self.budget_chars
        chunks: list[ContextChunk] = []
        summary = "\n".join(item.strip() for item in summaries or [] if item.strip())
        if summary:
            summary = summary[:remaining]
            remaining -= len(summary)

        if fresh_text.strip() and remaining > 0:
            fresh_tail = fresh_text[-min(self.fresh_tail_chars, remaining) :]
            chunks.append(ContextChunk(id="fresh_tail", text=fresh_tail, source="session"))
            remaining -= len(fresh_tail)

        for chunk in sorted(retrieved or [], key=lambda item: item.score or 0, reverse=True):
            if remaining <= 0:
                break
            text = chunk.text[:remaining]
            chunks.append(
                ContextChunk(
                    id=chunk.id,
                    text=text,
                    source=chunk.source,
                    score=chunk.score,
                    metadata=chunk.metadata,
                )
            )
            remaining -= len(text)

        return ContextPack(goal=goal, chunks=tuple(chunks), summary=summary, budget_chars=self.budget_chars)
