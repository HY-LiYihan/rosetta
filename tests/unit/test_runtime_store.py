import tempfile
import unittest
from pathlib import Path

from app.core.models import AnnotationTask, Project, WorkflowRun
from app.runtime.store import RuntimeStore


class TestRuntimeStore(unittest.TestCase):
    def test_store_projects_tasks_and_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RuntimeStore(Path(tmp) / "rosetta.sqlite3")
            store.upsert_project(Project(id="p1", name="Project"))
            store.upsert_task(AnnotationTask(id="t1", text="text"), project_id="p1")
            store.upsert_run(WorkflowRun(id="run1", workflow="annotation", status="succeeded"))

            self.assertEqual(store.list_projects()[0]["id"], "p1")
            self.assertEqual(store.list_tasks()[0]["project_id"], "p1")
            self.assertEqual(store.list_runs()[0]["workflow"], "annotation")


if __name__ == "__main__":
    unittest.main()
