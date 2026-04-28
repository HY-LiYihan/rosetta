import tempfile
import unittest
from pathlib import Path

from app.core.models import AnnotationOption, AnnotationSpan, AnnotationTask, Prediction
from app.data.prodigy_jsonl import prediction_from_dict, prediction_to_dict, read_tasks_jsonl, write_tasks_jsonl


class TestProdigyJsonl(unittest.TestCase):
    def test_task_jsonl_round_trip(self):
        task = AnnotationTask(
            id="s1",
            text="heart failure",
            spans=(AnnotationSpan(id="T1", start=0, end=13, text="heart failure", label="Term"),),
            options=(AnnotationOption(id="A", text="accept"),),
            accept=("A",),
            answer="accept",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tasks.jsonl"
            write_tasks_jsonl(path, [task])
            loaded = read_tasks_jsonl(path)
        self.assertEqual(loaded[0].id, "s1")
        self.assertEqual(loaded[0].spans[0].label, "Term")

    def test_prediction_round_trip(self):
        prediction = Prediction(
            id="p1",
            task_id="s1",
            source="model",
            model="glm-5",
            spans=(AnnotationSpan(id="T1", start=0, end=13, text="heart failure", label="Term"),),
            score=0.9,
        )
        payload = prediction_to_dict(prediction)
        loaded = prediction_from_dict(payload)
        self.assertEqual(loaded.model, "glm-5")
        self.assertEqual(loaded.score, 0.9)


if __name__ == "__main__":
    unittest.main()
