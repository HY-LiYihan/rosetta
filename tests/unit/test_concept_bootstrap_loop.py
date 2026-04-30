import json
import tempfile
import unittest
from pathlib import Path

from app.core.models import Project
from app.runtime.store import RuntimeStore
from app.workflows.bootstrap import gold_task_from_markup, run_concept_refinement_loop, save_guideline_package


def _store_with_guideline(gold_count: int = 15):
    tmp = tempfile.TemporaryDirectory()
    store = RuntimeStore(Path(tmp.name) / "rosetta.sqlite3")
    store.upsert_project(Project(id="p1", name="Project"))
    gold_tasks = [
        gold_task_from_markup(
            task_id=f"gold-{index:02d}",
            text=f"Quantum term {index} appears here.",
            annotation_markup=f"[Quantum term {index}]{{Term}} appears here.",
            label_hint="Term",
        )
        for index in range(gold_count)
    ]
    package = save_guideline_package(
        store,
        project_id="p1",
        name="Term",
        brief="Mark scientific terms.",
        labels=["Term"],
        boundary_rules=["Use the minimal complete term."],
        negative_rules=["Do not mark generic words."],
        gold_tasks=gold_tasks,
    )
    return tmp, store, package["guideline"].id


class TestConceptBootstrapLoop(unittest.TestCase):
    def test_requires_target_gold_count(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=3)
        self.addCleanup(tmp.cleanup)

        with self.assertRaisesRegex(ValueError, "15 条金样例"):
            run_concept_refinement_loop(store, guideline_id)

    def test_stops_when_all_gold_examples_pass(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)

        result = run_concept_refinement_loop(store, guideline_id, max_rounds=5)

        self.assertTrue(result["stable"])
        self.assertEqual(len(result["rounds"]), 1)
        self.assertEqual(result["rounds"][0]["pass_count"], 15)
        guideline = store.get_guideline(guideline_id)["payload"]
        self.assertEqual(guideline["status"], "stable")

    def test_writes_failure_versions_until_max_rounds(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)

        def bad_predictor(system_prompt, messages, temperature):
            text = messages[-1]["content"].split("文本：", 1)[-1].strip()
            return json.dumps({"text": text, "annotation": "[Wrong]{Term}", "explanation": "wrong"})

        result = run_concept_refinement_loop(store, guideline_id, predictor=bad_predictor, max_rounds=2)

        self.assertFalse(result["stable"])
        self.assertEqual(len(result["rounds"]), 2)
        self.assertEqual(result["rounds"][0]["pass_count"], 0)
        versions = store.list_concept_versions(guideline_id=guideline_id, limit=10)
        generated = [row for row in versions if row["payload"].get("metadata", {}).get("revision_source") == "concept_refinement_loop"]
        self.assertEqual(len(generated), 2)
        self.assertTrue(generated[0]["payload"]["metadata"]["failure_summary"])


if __name__ == "__main__":
    unittest.main()
