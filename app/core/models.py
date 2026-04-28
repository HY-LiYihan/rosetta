from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def utc_timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class AnnotationSpan:
    start: int
    end: int
    text: str
    label: str
    id: str = ""
    implicit: bool = False

    def validate(self, source_text: str) -> None:
        require_text(self.text, "span.text")
        require_text(self.label, "span.label")
        if self.implicit:
            if self.start != -1 or self.end != -1:
                raise ValueError("implicit span offsets must be -1")
            return
        if self.start < 0 or self.end <= self.start:
            raise ValueError(f"invalid span offsets for `{self.text}`")
        if self.end > len(source_text):
            raise ValueError(f"span `{self.text}` exceeds source text")
        if source_text[self.start : self.end] != self.text:
            raise ValueError(
                f"span text mismatch: expected `{self.text}`, got `{source_text[self.start:self.end]}`"
            )


@dataclass(frozen=True)
class AnnotationRelation:
    label: str
    id: str = ""
    head_span_id: str | None = None
    child_span_id: str | None = None
    head: int | None = None
    child: int | None = None

    def validate(self) -> None:
        require_text(self.label, "relation.label")
        has_span_relation = bool(self.head_span_id and self.child_span_id)
        has_token_relation = self.head is not None and self.child is not None
        if not has_span_relation and not has_token_relation:
            raise ValueError("relation must reference span ids or token indexes")


@dataclass(frozen=True)
class AnnotationOption:
    id: str
    text: str

    def validate(self) -> None:
        require_text(self.id, "option.id")
        require_text(self.text, "option.text")


@dataclass(frozen=True)
class AnnotationTask:
    id: str
    text: str
    tokens: tuple[dict[str, Any], ...] = ()
    spans: tuple[AnnotationSpan, ...] = ()
    relations: tuple[AnnotationRelation, ...] = ()
    label: str | None = None
    options: tuple[AnnotationOption, ...] = ()
    accept: tuple[str, ...] = ()
    answer: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        require_text(self.id, "task.id")
        require_text(self.text, "task.text")
        span_ids: set[str] = set()
        for index, span in enumerate(self.spans, start=1):
            span.validate(self.text)
            span_id = span.id or f"T{index}"
            if span_id in span_ids:
                raise ValueError(f"duplicated span id: {span_id}")
            span_ids.add(span_id)
        for relation in self.relations:
            relation.validate()
            if relation.head_span_id and relation.head_span_id not in span_ids:
                raise ValueError(f"unknown relation head_span_id: {relation.head_span_id}")
            if relation.child_span_id and relation.child_span_id not in span_ids:
                raise ValueError(f"unknown relation child_span_id: {relation.child_span_id}")
        option_ids = {option.id for option in self.options}
        for option in self.options:
            option.validate()
        unknown_accepts = [option_id for option_id in self.accept if option_id not in option_ids]
        if unknown_accepts and self.options:
            raise ValueError(f"accept references unknown options: {unknown_accepts}")


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    description: str = ""
    task_schema: str = "span"
    labels: tuple[str, ...] = ()
    guidelines: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_timestamp)

    def validate(self) -> None:
        require_text(self.id, "project.id")
        require_text(self.name, "project.name")
        require_text(self.task_schema, "project.task_schema")


@dataclass(frozen=True)
class ConceptGuideline:
    id: str
    project_id: str
    name: str
    brief: str
    labels: tuple[str, ...] = ()
    boundary_rules: tuple[str, ...] = ()
    negative_rules: tuple[str, ...] = ()
    output_format: str = "[原文]{标签}"
    stable_description: str = ""
    status: str = "draft"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_timestamp)

    def validate(self) -> None:
        require_text(self.id, "guideline.id")
        require_text(self.project_id, "guideline.project_id")
        require_text(self.name, "guideline.name")
        require_text(self.brief, "guideline.brief")
        if self.status not in {"draft", "validating", "stable", "needs_revision"}:
            raise ValueError(f"unknown guideline status: {self.status}")


@dataclass(frozen=True)
class GoldExampleSet:
    id: str
    project_id: str
    guideline_id: str
    task_ids: tuple[str, ...]
    target_count: int = 15
    status: str = "draft"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_timestamp)

    def validate(self) -> None:
        require_text(self.id, "gold_set.id")
        require_text(self.project_id, "gold_set.project_id")
        require_text(self.guideline_id, "gold_set.guideline_id")
        if self.target_count <= 0:
            raise ValueError("gold_set.target_count must be positive")
        if self.status not in {"draft", "validating", "passed", "needs_revision"}:
            raise ValueError(f"unknown gold set status: {self.status}")


@dataclass(frozen=True)
class ConceptVersion:
    id: str
    guideline_id: str
    version: int
    description: str
    failed_task_ids: tuple[str, ...] = ()
    unstable_task_ids: tuple[str, ...] = ()
    notes: str = ""
    created_at: str = field(default_factory=utc_timestamp)

    def validate(self) -> None:
        require_text(self.id, "concept_version.id")
        require_text(self.guideline_id, "concept_version.guideline_id")
        require_text(self.description, "concept_version.description")
        if self.version <= 0:
            raise ValueError("concept_version.version must be positive")


@dataclass(frozen=True)
class BatchJob:
    id: str
    project_id: str
    guideline_id: str
    status: str = "queued"
    sample_count: int = 5
    concurrency: int = 4
    review_threshold: float = 0.75
    auto_sample_rate: float = 0.05
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    review_items: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_timestamp)
    updated_at: str = field(default_factory=utc_timestamp)

    def validate(self) -> None:
        require_text(self.id, "job.id")
        require_text(self.project_id, "job.project_id")
        require_text(self.guideline_id, "job.guideline_id")
        if self.status not in {"queued", "running", "completed", "failed", "paused"}:
            raise ValueError(f"unknown job status: {self.status}")
        if self.sample_count <= 0:
            raise ValueError("job.sample_count must be positive")
        if self.concurrency <= 0:
            raise ValueError("job.concurrency must be positive")
        if not 0 <= self.review_threshold <= 1:
            raise ValueError("job.review_threshold must be between 0 and 1")
        if not 0 <= self.auto_sample_rate <= 1:
            raise ValueError("job.auto_sample_rate must be between 0 and 1")


@dataclass(frozen=True)
class BatchJobItem:
    id: str
    job_id: str
    task_id: str
    status: str = "queued"
    score: float | None = None
    route: str = "pending"
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_timestamp)
    updated_at: str = field(default_factory=utc_timestamp)

    def validate(self) -> None:
        require_text(self.id, "job_item.id")
        require_text(self.job_id, "job_item.job_id")
        require_text(self.task_id, "job_item.task_id")
        if self.status not in {"queued", "running", "completed", "failed"}:
            raise ValueError(f"unknown job item status: {self.status}")
        if self.score is not None and not 0 <= self.score <= 1:
            raise ValueError("job_item.score must be between 0 and 1")


@dataclass(frozen=True)
class Prediction:
    id: str
    task_id: str
    source: str
    model: str = ""
    spans: tuple[AnnotationSpan, ...] = ()
    relations: tuple[AnnotationRelation, ...] = ()
    label: str | None = None
    accept: tuple[str, ...] = ()
    answer: str | None = None
    score: float | None = None
    raw_response: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_timestamp)

    def validate(self) -> None:
        require_text(self.id, "prediction.id")
        require_text(self.task_id, "prediction.task_id")
        require_text(self.source, "prediction.source")
        if self.score is not None and not 0 <= self.score <= 1:
            raise ValueError("prediction.score must be between 0 and 1")


@dataclass(frozen=True)
class ReviewTask:
    id: str
    task_id: str
    question: str
    prediction_ids: tuple[str, ...] = ()
    options: tuple[AnnotationOption, ...] = ()
    answer: str | None = None
    status: str = "pending"
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_timestamp)

    def validate(self) -> None:
        require_text(self.id, "review.id")
        require_text(self.task_id, "review.task_id")
        require_text(self.question, "review.question")
        if self.status not in {"pending", "accepted", "rejected", "ignored"}:
            raise ValueError(f"unknown review status: {self.status}")


@dataclass(frozen=True)
class WorkflowRun:
    id: str
    workflow: str
    status: str = "created"
    input_ref: str = ""
    output_ref: str = ""
    artifacts: tuple[str, ...] = ()
    summary: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=utc_timestamp)
    ended_at: str | None = None

    def validate(self) -> None:
        require_text(self.id, "run.id")
        require_text(self.workflow, "run.workflow")
        if self.status not in {"created", "running", "succeeded", "failed", "cancelled"}:
            raise ValueError(f"unknown workflow status: {self.status}")


@dataclass(frozen=True)
class AgentStep:
    id: str
    run_id: str
    step_type: str
    name: str
    status: str = "succeeded"
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    created_at: str = field(default_factory=utc_timestamp)

    def validate(self) -> None:
        require_text(self.id, "agent_step.id")
        require_text(self.run_id, "agent_step.run_id")
        require_text(self.step_type, "agent_step.step_type")
        require_text(self.name, "agent_step.name")
        if self.status not in {"succeeded", "failed", "skipped"}:
            raise ValueError(f"unknown agent step status: {self.status}")
