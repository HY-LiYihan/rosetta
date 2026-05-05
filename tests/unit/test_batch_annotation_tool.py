import json
import tempfile
import unittest
from pathlib import Path

from app.core.models import Project
from app.data.exporters import build_dataset_stats, filter_tasks_for_export, rows_to_jsonl
from app.data.prodigy_jsonl import read_tasks_jsonl
from app.data.text_ingestion import split_sentences, tasks_from_csv, tasks_from_jsonl, tasks_from_txt, tokenize_text
from app.runtime.store import RuntimeStore
from app.workflows.annotation import run_batch_worker, submit_batch_annotation
from app.workflows.bootstrap import (
    FULL_JSON_OUTPUT_FORMAT,
    gold_task_from_markup,
    revise_guideline,
    save_guideline_package,
    validate_gold_examples,
)
from app.workflows.review import apply_review_decision, get_next_review_task, list_review_queue


class TestBatchAnnotationTool(unittest.TestCase):
    def test_text_ingestion_builds_tasks(self):
        sentences = split_sentences("Alpha tests. 第二句可以工作。第三句！")
        self.assertEqual(sentences, ["Alpha tests.", "第二句可以工作。", "第三句！"])
        self.assertEqual(tokenize_text("A股"), [{"id": 0, "text": "A", "start": 0, "end": 1}, {"id": 1, "text": "股", "start": 1, "end": 2}])

        txt_tasks = tasks_from_txt("heart failure is common.", prefix="txt")
        self.assertEqual(txt_tasks[0].id, "txt-00001")

        jsonl_tasks = tasks_from_jsonl('{"id":"j1","text":"renal failure"}\n')
        self.assertEqual(jsonl_tasks[0].id, "j1")

        csv_tasks = tasks_from_csv("text,source\nheart failure,a\n", text_column="text")
        self.assertEqual(csv_tasks[0].meta["source_format"], "csv")

    def test_guideline_validation_and_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RuntimeStore(Path(tmp) / "rosetta.sqlite3")
            store.upsert_project(Project(id="p1", name="Project"))
            gold = gold_task_from_markup("g1", "heart failure is common", "[heart failure]{Term}", "Term")
            package = save_guideline_package(
                store,
                project_id="p1",
                name="Term",
                brief="标出医学术语",
                labels=["Term"],
                boundary_rules=["最小完整术语"],
                negative_rules=["不标普通词"],
                gold_tasks=[gold],
            )

            result = validate_gold_examples(store, package["guideline"].id)
            self.assertEqual(result["status"], "stable")
            self.assertEqual(result["passed"], ["g1"])
            revised = revise_guideline({"stable_description": "旧描述"}, {"failed": ["g2"], "unstable": []})
            self.assertIn("边界补充", revised)
            self.assertNotIn("失败样例范围", revised)
            self.assertNotIn("g2", revised)

    def test_guideline_infers_label_and_stores_format_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RuntimeStore(Path(tmp) / "rosetta.sqlite3")
            store.upsert_project(Project(id="p1", name="Project"))
            gold = gold_task_from_markup("g1", "heart failure is common", "[heart failure]{DiseaseTerm}", "")
            package = save_guideline_package(
                store,
                project_id="p1",
                name="Term",
                brief="标出医学术语",
                labels=None,
                boundary_rules=["最小完整术语"],
                negative_rules=None,
                gold_tasks=[gold],
                output_format=FULL_JSON_OUTPUT_FORMAT,
            )

            guideline = store.get_guideline(package["guideline"].id)["payload"]
            self.assertEqual(guideline["labels"], ["DiseaseTerm"])
            self.assertEqual(guideline["output_format"], FULL_JSON_OUTPUT_FORMAT)
            self.assertNotIn("标签集合", guideline["stable_description"])
            self.assertNotIn("输出格式", guideline["stable_description"])

    def test_batch_worker_review_and_export_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RuntimeStore(Path(tmp) / "rosetta.sqlite3")
            store.upsert_project(Project(id="p1", name="Project"))
            gold = gold_task_from_markup("g1", "heart failure is common", "[heart failure]{Term}", "Term")
            package = save_guideline_package(
                store,
                project_id="p1",
                name="Term",
                brief="标出医学术语",
                labels=["Term"],
                boundary_rules=[],
                negative_rules=[],
                gold_tasks=[gold],
            )
            tasks = tasks_from_txt("heart failure is common.", prefix="batch")
            job = submit_batch_annotation(
                store,
                project_id="p1",
                guideline_id=package["guideline"].id,
                tasks=tasks,
                sample_count=1,
                concurrency=1,
                review_threshold=0.99,
                auto_sample_rate=0.0,
            )

            def predictor(system_prompt, messages, temperature):
                return json.dumps(
                    {
                        "text": "heart failure is common.",
                        "annotation": "[heart failure]{Term}",
                        "explanation": "医学术语。",
                        "confidence": 0.8,
                    },
                    ensure_ascii=False,
                )

            result = run_batch_worker(store, job.id, predictor, platform="mock", model="mock")
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["review_items"], 1)

            queue = list_review_queue(store, threshold=0.99)
            self.assertEqual(len(queue), 1)
            card = get_next_review_task(store, threshold=0.99)
            self.assertEqual(card["task"]["text"], "heart failure is common.")

            decision = apply_review_decision(store, card["review"]["id"], decision="accept", selected_option_id="A")
            self.assertEqual(decision["status"], "accepted")

            tasks_after = store.list_tasks(limit=10)
            stats = build_dataset_stats(tasks_after, store.list_predictions(), store.list_reviews(), store.list_jobs())
            self.assertEqual(stats["accepted_review_count"], 1)
            reviewed = filter_tasks_for_export(tasks_after, "reviewed")
            self.assertEqual(len(reviewed), 1)

            path = Path(tmp) / "reviewed.jsonl"
            path.write_text(rows_to_jsonl(reviewed), encoding="utf-8")
            roundtrip = read_tasks_jsonl(path)
            self.assertEqual(roundtrip[0].answer, "accept")


if __name__ == "__main__":
    unittest.main()
