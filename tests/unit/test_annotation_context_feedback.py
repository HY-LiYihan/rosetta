import tempfile
import unittest
from pathlib import Path

from app.core.models import AnnotationSpan, AnnotationTask, Prediction, Project, ReviewTask, AnnotationOption
from app.runtime.store import RuntimeStore
from app.workflows.annotation import build_annotation_context, score_candidates
from app.workflows.bootstrap import gold_task_from_markup, save_guideline_package
from app.workflows.review import apply_review_decision


def _setup_store():
    tmp = tempfile.TemporaryDirectory()
    store = RuntimeStore(Path(tmp.name) / "rosetta.sqlite3")
    store.upsert_project(Project(id="p1", name="Project"))
    gold_tasks = [
        gold_task_from_markup(
            task_id=f"gold-{index:02d}",
            text=f"Quantum dots sample {index}.",
            annotation_markup="[Quantum dots]{Term} sample.",
            label_hint="Term",
        )
        for index in range(3)
    ]
    package = save_guideline_package(
        store,
        project_id="p1",
        name="Term",
        brief="Mark hard science terms.",
        labels=["Term"],
        boundary_rules=["Use minimal complete terms."],
        negative_rules=["Do not mark generic words."],
        gold_tasks=gold_tasks,
    )
    target = AnnotationTask(id="target", text="Quantum dots emit light.")
    store.upsert_task(target, project_id="p1")
    return tmp, store, package["guideline"].id, target.id


class TestAnnotationContextFeedback(unittest.TestCase):
    def test_context_builder_returns_examples_and_failure_memory(self):
        tmp, store, guideline_id, task_id = _setup_store()
        self.addCleanup(tmp.cleanup)

        context = build_annotation_context(store, guideline_id, task_id, similar_k=2, boundary_k=1, failure_k=2)

        self.assertIn("Mark hard science terms", context["prompt"])
        self.assertNotIn("模型输出格式", context["prompt"])
        self.assertNotIn("[span]{Term}", context["prompt"])
        self.assertEqual(len(context["similar_examples"]), 2)
        self.assertEqual(len(context["boundary_examples"]), 1)
        self.assertEqual(len(context["context_example_ids"]), 3)
        self.assertTrue(context["examples"][0]["annotation"])

    def test_score_candidates_uses_span_f1_and_rule_risk(self):
        span = AnnotationSpan(id="T1", start=0, end=12, text="Quantum dots", label="Term")
        matching = Prediction(id="p1", task_id="t1", source="batch", spans=(span,), score=0.9, meta={"rule_risk": 0.0})
        missing = Prediction(id="p2", task_id="t1", source="batch", spans=(), score=0.4, meta={"rule_risk": 0.5})

        score = score_candidates([matching, missing])

        self.assertLess(score["agreement"], 1.0)
        self.assertGreater(score["score"], 0.0)
        self.assertEqual(len(score["candidate_scores"]), 2)
        self.assertIn("span_f1_to_consensus", score["candidate_scores"][0])

    def test_review_decision_records_feedback_metadata(self):
        tmp, store, _guideline_id, _task_id = _setup_store()
        self.addCleanup(tmp.cleanup)
        task = AnnotationTask(id="review-task", text="Quantum dots emit light.")
        store.upsert_task(task, project_id="p1")
        span = AnnotationSpan(id="T1", start=0, end=12, text="Quantum dots", label="Term")
        prediction = Prediction(id="pred-1", task_id=task.id, source="batch", spans=(span,), score=0.6)
        store.upsert_prediction(prediction)
        review = ReviewTask(
            id="review-1",
            task_id=task.id,
            question="Choose",
            prediction_ids=(prediction.id,),
            options=(AnnotationOption(id="A", text="Quantum dots / Term"),),
        )
        store.upsert_review(review)

        apply_review_decision(
            store,
            review_id=review.id,
            decision="accept",
            selected_option_id="A",
            note="ok",
            hard_example=True,
            error_type="boundary",
            promote_to_gold=True,
        )

        updated_task = store.get_task(task.id)["payload"]
        updated_review = store.get_review(review.id)["payload"]
        self.assertTrue(updated_task["meta"]["hard_example"])
        self.assertTrue(updated_task["meta"]["promote_to_gold"])
        self.assertEqual(updated_task["meta"]["source_pool"], "gold_like")
        self.assertEqual(updated_review["meta"]["selected_candidate_id"], "pred-1")
        self.assertEqual(updated_review["meta"]["error_type"], "boundary")


if __name__ == "__main__":
    unittest.main()
