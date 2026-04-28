from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.models import AgentStep, WorkflowRun, utc_timestamp
from app.agents.context import ContextEngine, ContextPack
from app.agents.tools import ToolRegistry


@dataclass(frozen=True)
class AgentPolicy:
    model: str = ""
    temperature: float = 0.3
    sample_count: int = 1
    max_retries: int = 1
    require_human_review: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentContext:
    goal: str
    state: dict[str, Any] = field(default_factory=dict)
    context_pack: ContextPack | None = None


@dataclass(frozen=True)
class AgentResult:
    run: WorkflowRun
    state: dict[str, Any]
    steps: tuple[AgentStep, ...]
    ok: bool
    error: str = ""


class AgentKernel:
    def __init__(self, context_engine: ContextEngine | None = None):
        self.context_engine = context_engine or ContextEngine()

    def run(
        self,
        goal: str,
        context: AgentContext | dict[str, Any] | None,
        tools: ToolRegistry,
        policy: AgentPolicy | None = None,
        tool_plan: list[str] | None = None,
        workflow: str = "agent",
    ) -> AgentResult:
        resolved_policy = policy or AgentPolicy()
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        state = self._initial_state(goal, context, resolved_policy)
        run = WorkflowRun(id=run_id, workflow=workflow, status="running", meta={"policy": resolved_policy.metadata})
        steps: list[AgentStep] = []

        for tool_name in tool_plan or tools.names():
            step_id = f"step-{uuid.uuid4().hex[:12]}"
            try:
                output = tools.run(tool_name, state)
                if output:
                    state.update(output)
                steps.append(
                    AgentStep(
                        id=step_id,
                        run_id=run_id,
                        step_type="tool",
                        name=tool_name,
                        input={"state_keys": sorted(state.keys())},
                        output=output,
                    )
                )
            except Exception as exc:  # pragma: no cover - exact exception type belongs to the tool
                steps.append(
                    AgentStep(
                        id=step_id,
                        run_id=run_id,
                        step_type="tool",
                        name=tool_name,
                        status="failed",
                        input={"state_keys": sorted(state.keys())},
                        error=str(exc),
                    )
                )
                failed = WorkflowRun(
                    id=run.id,
                    workflow=run.workflow,
                    status="failed",
                    input_ref=run.input_ref,
                    output_ref=run.output_ref,
                    artifacts=run.artifacts,
                    summary=run.summary,
                    meta=run.meta,
                    started_at=run.started_at,
                    ended_at=utc_timestamp(),
                )
                return AgentResult(run=failed, state=state, steps=tuple(steps), ok=False, error=str(exc))

        succeeded = WorkflowRun(
            id=run.id,
            workflow=run.workflow,
            status="succeeded",
            input_ref=run.input_ref,
            output_ref=run.output_ref,
            artifacts=run.artifacts,
            summary=run.summary,
            meta=run.meta,
            started_at=run.started_at,
            ended_at=utc_timestamp(),
        )
        return AgentResult(run=succeeded, state=state, steps=tuple(steps), ok=True)

    def _initial_state(
        self,
        goal: str,
        context: AgentContext | dict[str, Any] | None,
        policy: AgentPolicy,
    ) -> dict[str, Any]:
        if isinstance(context, AgentContext):
            state = dict(context.state)
            state.setdefault("goal", context.goal or goal)
            if context.context_pack is not None:
                state.setdefault("context_pack", context.context_pack)
        else:
            state = dict(context or {})
            state.setdefault("goal", goal)
        state.setdefault("policy", policy)
        return state
