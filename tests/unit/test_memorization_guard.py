import tempfile
import unittest
from pathlib import Path

from app.core.models import Project
from app.runtime.store import RuntimeStore
from app.workflows.bootstrap import MemorizationGuard, gold_task_from_markup


class TestMemorizationGuard(unittest.TestCase):
    def _store_with_gold(self):
        tmp = tempfile.TemporaryDirectory()
        store = RuntimeStore(Path(tmp.name) / "rosetta.sqlite3")
        store.upsert_project(Project(id="p1", name="Project"))
        task = gold_task_from_markup(
            task_id="gold-00001",
            text="Quantum term 1 appears here.",
            annotation_markup="[Quantum term 1]{Term} appears here.",
            label_hint="Term",
        )
        store.upsert_task(task)
        return tmp, store

    def test_blocks_gold_text_span_and_ngram_without_raw_terms(self):
        tmp, store = self._store_with_gold()
        self.addCleanup(tmp.cleanup)
        guard = MemorizationGuard.from_store(store, ["gold-00001"], allowed_terms=["Term"])

        self.assertFalse(guard.check("边界规则：Quantum term 加编号时整体标注。").passed)
        self.assertFalse(guard.check("边界规则：appears here 这类语境应整体处理。").passed)
        self.assertTrue(guard.check("标签集合：Term").passed)

    def test_blocks_model_span_after_validation_feedback(self):
        tmp, store = self._store_with_gold()
        self.addCleanup(tmp.cleanup)
        guard = MemorizationGuard.from_store(store, ["gold-00001"], allowed_terms=["Term"])
        validation_result = {
            "details": [
                {
                    "predicted_spans": [
                        {"text": "Wrong model span", "label": "Term"},
                    ]
                }
            ]
        }

        round_guard = guard.with_validation_result(validation_result)

        self.assertFalse(round_guard.check("排除规则：不要把 Wrong model span 写入提示词。").passed)
        self.assertTrue(guard.check("排除规则：候选答案只能抽象成规则。").passed)


if __name__ == "__main__":
    unittest.main()
