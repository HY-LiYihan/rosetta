from __future__ import annotations

import json
import logging

from app.domain.schemas import DATA_VERSION
from app.domain.validators import normalize_payload

logger = logging.getLogger(__name__)


class JsonConceptRepository:
    def __init__(self, file_path: str = "assets/concepts.json"):
        self.file_path = file_path

    def load(self) -> tuple[list[dict], str]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        normalized = normalize_payload(payload)
        return normalized["concepts"], normalized.get("version", DATA_VERSION)

    def save(self, concepts: list[dict], version: str) -> None:
        payload = {"version": version, "concepts": concepts}
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")


def load_concepts_with_fallback(file_path: str) -> tuple[list[dict], str]:
    """Repository-backed load with compatibility fallback behavior."""
    default_concept = {
        "name": "默认",
        "prompt": "默认",
        "examples": [{"text": "默认", "annotation": "默认", "explanation": "默认"}],
        "category": "默认",
        "is_default": True,
    }
    try:
        repo = JsonConceptRepository(file_path=file_path)
        concepts, version = repo.load()
        if concepts:
            return concepts, version
    except FileNotFoundError:
        logger.warning("Concept file not found, fallback to default concept: %s", file_path)
    except Exception as e:
        logger.exception("Failed to load concepts from %s, fallback to default. error=%s", file_path, e)

    return [default_concept], DATA_VERSION
