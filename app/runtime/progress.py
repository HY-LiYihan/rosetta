from __future__ import annotations

import time
import uuid
from threading import Lock
from typing import Any

from app.core.models import RunProgressEvent
from app.runtime.store import RuntimeStore

PROMPT_TRAINING_WORKFLOW = "prompt_training"

_REDACTED_KEYS = {
    "annotation",
    "best_description",
    "candidate_description",
    "content",
    "current_description",
    "description",
    "extra_spans",
    "forbidden",
    "gold_spans",
    "leaked_terms",
    "messages",
    "missing_spans",
    "predicted_spans",
    "private_matches",
    "prompt",
    "raw_prompt",
    "raw_response",
    "raw_revision_response",
    "response",
    "source_text",
    "text",
}


def estimate_prompt_training_total_calls(method_count: int, max_rounds: int, gold_count: int, candidate_count: int) -> int:
    """Estimate upper-bound LLM calls for prompt training progress display."""

    methods = max(1, int(method_count))
    rounds = max(1, int(max_rounds))
    gold = max(1, int(gold_count))
    candidates = max(1, int(candidate_count))
    return methods * rounds * (gold * (1 + candidates) + candidates)


class ProgressRecorder:
    """Persist safe workflow progress events for realtime UI polling."""

    def __init__(
        self,
        store: RuntimeStore,
        run_id: str,
        workflow: str = PROMPT_TRAINING_WORKFLOW,
        estimated_total: int = 0,
    ) -> None:
        self.store = store
        self.run_id = run_id
        self.workflow = workflow
        self.estimated_total = max(0, int(estimated_total))
        self.started_at = time.monotonic()
        self._lock = Lock()
        self.completed = 0
        self.running = 0
        self.failed = 0
        self.total_tokens = 0
        self.llm_call_count = 0
        self.retry_count = 0
        self.repair_attempt_count = 0
        self.best_method = ""
        self.best_pass_count = 0
        self.best_loss: float | None = None

    def emit(
        self,
        event_type: str,
        *,
        stage: str = "",
        message: str = "",
        progress: float | None = None,
        completed: int | None = None,
        total: int | None = None,
        running: int | None = None,
        failed: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> RunProgressEvent:
        safe_payload = sanitize_progress_payload(payload or {})
        with self._lock:
            if completed is not None:
                self.completed = max(0, int(completed))
            if total is not None:
                self.estimated_total = max(0, int(total))
            if running is not None:
                self.running = max(0, int(running))
            if failed is not None:
                self.failed = max(0, int(failed))
            self._merge_summary_payload(safe_payload)
            completed_value = self.completed
            total_value = self.estimated_total
            running_value = self.running
            failed_value = self.failed
            progress_value = self._progress(progress, completed_value, total_value, event_type)
            safe_payload = {
                **safe_payload,
                "elapsed_seconds": round(time.monotonic() - self.started_at, 2),
                "eta_seconds": self._eta_seconds(completed_value, total_value),
                "llm_call_count": self.llm_call_count,
                "total_tokens": self.total_tokens,
                "retry_count": self.retry_count,
                "repair_attempt_count": self.repair_attempt_count,
                "best_method": self.best_method,
                "best_pass_count": self.best_pass_count,
                "best_loss": self.best_loss,
            }

        event = RunProgressEvent(
            id=f"run-event-{uuid.uuid4().hex[:12]}",
            run_id=self.run_id,
            workflow=self.workflow,
            event_type=event_type,
            stage=stage,
            message=message,
            progress=progress_value,
            completed=completed_value,
            total=total_value,
            running=running_value,
            failed=failed_value,
            payload=safe_payload,
        )
        self.store.add_run_progress_event(event)
        return event

    def event_sink(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("event_type") or "llm_event")
        metadata = dict(event.get("metadata") or {})
        completed = event.get("completed")
        running = event.get("running")
        failed = None
        if event_type == "call_failed":
            with self._lock:
                self.failed += 1
                failed = self.failed
        if event_type == "call_retried":
            with self._lock:
                self.retry_count += 1
        if event_type == "call_succeeded":
            with self._lock:
                self.llm_call_count = max(self.llm_call_count, int(completed or 0))
                self.total_tokens += int(metadata.get("total_tokens", 0) or 0)
        self.emit(
            event_type,
            stage=str(metadata.get("stage") or "模型调用"),
            message=_llm_event_message(event_type),
            completed=int(completed) if completed is not None else None,
            running=int(running) if running is not None else None,
            failed=failed,
            payload={
                "provider": event.get("provider"),
                "model": event.get("model"),
                "item_index": event.get("item_index"),
                "metadata": metadata,
            },
        )

    def summary(self) -> dict[str, Any]:
        latest = self.store.get_latest_run_progress(self.run_id)
        with self._lock:
            return {
                "run_id": self.run_id,
                "workflow": self.workflow,
                "completed": self.completed,
                "total": self.estimated_total,
                "running": self.running,
                "failed": self.failed,
                "progress": latest.get("progress") if latest else 0.0,
                "llm_call_count": self.llm_call_count,
                "total_tokens": self.total_tokens,
                "retry_count": self.retry_count,
                "repair_attempt_count": self.repair_attempt_count,
                "best_method": self.best_method,
                "best_pass_count": self.best_pass_count,
                "best_loss": self.best_loss,
                "elapsed_seconds": round(time.monotonic() - self.started_at, 2),
            }

    def list_events(self, limit: int = 2000) -> list[dict[str, Any]]:
        return self.store.list_run_progress_events(self.run_id, limit=limit)

    def _merge_summary_payload(self, payload: dict[str, Any]) -> None:
        if "repair_attempt_count" in payload:
            self.repair_attempt_count = max(self.repair_attempt_count, int(payload.get("repair_attempt_count") or 0))
        if "best_method" in payload and payload.get("best_method"):
            self.best_method = str(payload["best_method"])
        if "best_pass_count" in payload:
            self.best_pass_count = max(self.best_pass_count, int(payload.get("best_pass_count") or 0))
        if "best_loss" in payload and payload.get("best_loss") is not None:
            best_loss = float(payload["best_loss"])
            self.best_loss = best_loss if self.best_loss is None else min(self.best_loss, best_loss)

    def _progress(self, progress: float | None, completed: int, total: int, event_type: str) -> float:
        if progress is not None:
            return max(0.0, min(float(progress), 1.0))
        if event_type in {"run_completed", "outputs_written"}:
            return 1.0
        if total <= 0:
            return 0.0
        return max(0.0, min(completed / total, 0.99))

    def _eta_seconds(self, completed: int, total: int) -> float | None:
        if completed <= 0 or total <= 0 or completed >= total:
            return None
        elapsed = time.monotonic() - self.started_at
        return round((elapsed / completed) * max(0, total - completed), 2)


def sanitize_progress_payload(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[redacted: nested payload]"
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text in _REDACTED_KEYS or key_text.lower() in _REDACTED_KEYS:
                safe[key_text] = "[redacted]"
            else:
                safe[key_text] = sanitize_progress_payload(item, depth=depth + 1)
        return safe
    if isinstance(value, list):
        return [sanitize_progress_payload(item, depth=depth + 1) for item in value[:100]]
    if isinstance(value, tuple):
        return [sanitize_progress_payload(item, depth=depth + 1) for item in list(value)[:100]]
    if isinstance(value, str):
        return value if len(value) <= 500 else value[:500] + "..."
    return value


def _llm_event_message(event_type: str) -> str:
    return {
        "call_queued": "模型调用已排队",
        "call_started": "模型调用开始",
        "call_succeeded": "模型调用完成",
        "call_failed": "模型调用失败",
        "call_retried": "模型调用重试",
    }.get(event_type, "模型调用事件")
