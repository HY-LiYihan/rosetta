from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Skill:
    name: str
    instruction: str
    examples: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    def prompt_block(self) -> str:
        example_block = "\n".join(f"- {example}" for example in self.examples)
        if example_block:
            return f"## {self.name}\n{self.instruction}\n\nExamples:\n{example_block}"
        return f"## {self.name}\n{self.instruction}"


TERM_EXTRACTION = Skill(
    name="term_extraction",
    instruction="Identify explicit terminology spans and return parseable structured output.",
)

RELATION_ANNOTATION = Skill(
    name="relation_annotation",
    instruction="Identify relationships between existing spans using stable span ids.",
)

CORPUS_WRITER = Skill(
    name="corpus_writer",
    instruction="Generate corpus items grounded in the provided brief, constraints, and context pack.",
)

LLM_JUDGE = Skill(
    name="llm_judge",
    instruction="Evaluate candidate annotations or generated corpus items with concise, auditable reasons.",
)
