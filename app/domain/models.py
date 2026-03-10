from dataclasses import dataclass


@dataclass
class Example:
    text: str
    annotation: str
    explanation: str = ""


@dataclass
class Concept:
    name: str
    prompt: str
    examples: list[Example]
    category: str
    is_default: bool


@dataclass
class AnnotationRecord:
    timestamp: str
    concept: str
    text: str
    annotation: str
    platform: str | None
    model: str | None
    temperature: float
