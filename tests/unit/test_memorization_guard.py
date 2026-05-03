import tempfile
import unittest
from pathlib import Path

from app.core.models import AnnotationTask, Project
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
        plain = AnnotationTask(id="plain-00001", text="The telescope observed faint light.")
        store.upsert_task(plain)
        guard = MemorizationGuard.from_store(store, ["gold-00001"], allowed_terms=["Term"])
        source_guard = MemorizationGuard.from_store(store, ["plain-00001"], allowed_terms=["Term"])

        gold_span_check = guard.check("边界规则：Quantum term 加编号时整体标注。")
        source_ngram_check = source_guard.check("边界规则：observed faint 这类语境应整体处理。")
        self.assertFalse(gold_span_check.passed)
        self.assertEqual(gold_span_check.severity, "critical_leak")
        self.assertFalse(source_ngram_check.passed)
        self.assertEqual(source_ngram_check.severity, "soft_leak")
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

        check = round_guard.check("排除规则：不要把 Wrong model span 写入提示词。")
        self.assertFalse(check.passed)
        self.assertEqual(check.severity, "critical_leak")
        self.assertTrue(check.private_matches)
        self.assertTrue(guard.check("排除规则：候选答案只能抽象成规则。").passed)


if __name__ == "__main__":
    unittest.main()
