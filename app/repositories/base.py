from __future__ import annotations

from typing import Protocol


class ConceptRepository(Protocol):
    def load(self) -> tuple[list[dict], str]:
        """Load concepts and data version."""

    def save(self, concepts: list[dict], version: str) -> None:
        """Persist concepts and data version."""
