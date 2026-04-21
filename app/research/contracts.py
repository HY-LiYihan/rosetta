from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResearchExample:
    id: str
    text: str
    annotation: str
    explanation: str
    rationale: str = ""
    example_type: str = "canonical"


@dataclass(frozen=True)
class ConflictRule:
    name: str
    labels: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class ResearchSample:
    id: str
    text: str
    gold_annotation: str | None = None
    gold_explanation: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchConfig:
    name: str
    description: str
    platform: str
    model: str
    api_key_env: str
    api_key_secret: str | None
    system_prompt: str
    definition: str
    inclusion_rules: tuple[str, ...]
    exclusion_rules: tuple[str, ...]
    negative_constraints: tuple[str, ...]
    output_contract: tuple[str, ...]
    temperature: float
    top_k_examples: int
    retrieval_strategy: str
    output_dir: str
    index_dir: str
    embedding_model: str | None
    embedding_dimensions: int | None
    canonical_examples: tuple[ResearchExample, ...]
    hard_examples: tuple[ResearchExample, ...]
    conflict_rules: tuple[ConflictRule, ...]

    @property
    def example_bank(self) -> tuple[ResearchExample, ...]:
        return self.canonical_examples + self.hard_examples
