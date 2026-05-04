import re
import tempfile
import unittest
from pathlib import Path

from app.core.models import AnnotationTask, Project
from app.data.official_sample import (
    OFFICIAL_CONCEPT_VERSION_ID,
    OFFICIAL_GOLD_SET_ID,
    OFFICIAL_GUIDELINE_ID,
    OFFICIAL_PROJECT_ID,
    PROFESSIONAL_NER_EXAMPLE,
    professional_ner_description,
    professional_ner_gold_tasks,
)
from app.runtime.official_seed import reset_runtime_to_official_sample
from app.runtime.store import RuntimeStore


class TestOfficialSeed(unittest.TestCase):
    def test_reset_creates_single_official_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RuntimeStore(Path(tmp) / "rosetta.sqlite3")

            result = reset_runtime_to_official_sample(store)

            self.assertEqual(result["status"], "seeded")
            self.assertEqual(result["gold_count"], 15)
            self.assertEqual([row["id"] for row in store.list_projects(limit=10)], [OFFICIAL_PROJECT_ID])
            self.assertEqual([row["id"] for row in store.list_guidelines(limit=10)], [OFFICIAL_GUIDELINE_ID])
            self.assertEqual([row["id"] for row in store.list_gold_example_sets(limit=10)], [OFFICIAL_GOLD_SET_ID])
            self.assertEqual([row["id"] for row in store.list_concept_versions(limit=10)], [OFFICIAL_CONCEPT_VERSION_ID])
            self.assertEqual(len(store.list_tasks(limit=100)), 15)

            project = store.get_project(OFFICIAL_PROJECT_ID)
            guideline = store.get_guideline(OFFICIAL_GUIDELINE_ID)
            self.assertTrue(project["payload"]["metadata"]["official_sample"])
            self.assertEqual(project["payload"]["name"], "专业命名实体标注")
            self.assertEqual(guideline["payload"]["name"], "专业命名实体")
            self.assertEqual(guideline["payload"]["labels"], ["Term"])
            self.assertEqual(guideline["payload"]["stable_description"], professional_ner_description())

    def test_reset_clears_dirty_runtime_rows_without_touching_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RuntimeStore(Path(tmp) / "rosetta.sqlite3")
            artifact = Path(tmp) / "experiments" / "comparison_report.pdf"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("keep me", encoding="utf-8")
            store.upsert_project(Project(id="dirty-project", name="Dirty"))
            store.upsert_task(AnnotationTask(id="dirty-task", text="dirty text"), project_id="dirty-project")
            with store.connect() as conn:
                conn.execute(
                    "INSERT INTO predictions (id, task_id, payload, created_at) VALUES (?, ?, ?, ?)",
                    ("dirty-prediction", "dirty-task", "{}", "2026-05-04T00:00:00Z"),
                )
                conn.execute(
                    "INSERT INTO runs (id, workflow, status, payload, started_at) VALUES (?, ?, ?, ?, ?)",
                    ("dirty-run", "test", "running", "{}", "2026-05-04T00:00:00Z"),
                )
                conn.execute(
                    "INSERT INTO run_progress_events (id, run_id, workflow, event_type, created_at) VALUES (?, ?, ?, ?, ?)",
                    ("dirty-event", "dirty-run", "test", "run_started", "2026-05-04T00:00:00Z"),
                )

            reset_runtime_to_official_sample(store)

            self.assertIsNone(store.get_project("dirty-project"))
            self.assertIsNone(store.get_task("dirty-task"))
            self.assertEqual(store.list_predictions(limit=10), [])
            self.assertEqual(store.list_runs(limit=10), [])
            self.assertEqual(store.list_run_progress_events("dirty-run"), [])
            self.assertEqual(len(store.list_tasks(limit=100)), 15)
            self.assertTrue(artifact.exists())

    def test_official_operational_prompt_does_not_include_gold_answer_terms(self):
        description = professional_ner_description().lower()
        for row in PROFESSIONAL_NER_EXAMPLE["gold_examples"]:
            for term in re.findall(r"\[([^\]]+)\]\{Term\}", row["annotation"]):
                with self.subTest(term=term):
                    self.assertNotIn(term.lower(), description)

    def test_official_gold_tasks_are_valid_term_tasks(self):
        tasks = professional_ner_gold_tasks()

        self.assertEqual(len(tasks), 15)
        self.assertEqual(tasks[0].id, "official-gold-00001")
        self.assertTrue(all(task.spans for task in tasks))
        self.assertTrue(all(span.label == "Term" for task in tasks for span in task.spans))


if __name__ == "__main__":
    unittest.main()
