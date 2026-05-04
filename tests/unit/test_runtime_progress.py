import tempfile
import time
import unittest
from pathlib import Path

from app.core.models import RunProgressEvent, WorkflowRun
from app.runtime.progress import ProgressRecorder, estimate_prompt_training_total_calls
from app.runtime.store import RuntimeStore


class TestRuntimeProgress(unittest.TestCase):
    def test_store_writes_and_filters_run_progress_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RuntimeStore(Path(tmp) / "rosetta.sqlite3")
            store.upsert_run(WorkflowRun(id="run-1", workflow="prompt_training", status="running"))
            store.add_run_progress_event(
                RunProgressEvent(
                    id="event-1",
                    run_id="run-1",
                    workflow="prompt_training",
                    event_type="round_started",
                    stage="训练轮次",
                    progress=0.2,
                    completed=2,
                    total=10,
                    payload={"method": "llm_reflection"},
                )
            )
            store.add_run_progress_event(
                RunProgressEvent(
                    id="event-2",
                    run_id="run-1",
                    workflow="prompt_training",
                    event_type="round_completed",
                    stage="训练轮次",
                    progress=0.3,
                    completed=3,
                    total=10,
                    payload={"method": "llm_reflection"},
                )
            )

            events = store.list_run_progress_events("run-1", event_type="round_completed")
            latest = store.get_latest_run_progress("run-1")

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["event_type"], "round_completed")
            self.assertEqual(events[0]["payload"]["method"], "llm_reflection")
            self.assertEqual(latest["id"], "event-2")

    def test_progress_recorder_sanitizes_payload_and_computes_eta(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RuntimeStore(Path(tmp) / "rosetta.sqlite3")
            store.upsert_run(WorkflowRun(id="run-1", workflow="prompt_training", status="running"))
            recorder = ProgressRecorder(store, "run-1", estimated_total=10)

            first = recorder.emit(
                "candidate_evaluated",
                stage="候选回测",
                completed=0,
                payload={
                    "method": "text_gradient_adamw",
                    "raw_prompt": "secret prompt",
                    "messages": [{"content": "secret source"}],
                },
            )
            time.sleep(0.01)
            second = recorder.emit("call_succeeded", stage="模型调用", completed=2)

            self.assertIsNone(first.payload["eta_seconds"])
            self.assertIsNotNone(second.payload["eta_seconds"])
            self.assertEqual(first.payload["raw_prompt"], "[redacted]")
            self.assertEqual(first.payload["messages"], "[redacted]")

    def test_prompt_training_total_call_estimate(self):
        self.assertEqual(estimate_prompt_training_total_calls(3, 30, 15, 3), 5670)


if __name__ == "__main__":
    unittest.main()
