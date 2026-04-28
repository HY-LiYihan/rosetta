import unittest

from app.core.models import AnnotationOption, AnnotationSpan, AnnotationTask, Prediction, Project, ReviewTask


class TestCoreModels(unittest.TestCase):
    def test_annotation_task_validates_spans_and_options(self):
        task = AnnotationTask(
            id="t1",
            text="heart failure",
            spans=(AnnotationSpan(id="T1", start=0, end=13, text="heart failure", label="Term"),),
            options=(AnnotationOption(id="accept", text="Accept"),),
            accept=("accept",),
        )
        task.validate()

    def test_annotation_task_rejects_bad_offset(self):
        task = AnnotationTask(
            id="t1",
            text="heart failure",
            spans=(AnnotationSpan(start=0, end=5, text="failure", label="Term"),),
        )
        with self.assertRaises(ValueError):
            task.validate()

    def test_project_prediction_and_review_validate(self):
        Project(id="p1", name="Project").validate()
        Prediction(id="pred1", task_id="t1", source="model", score=0.5).validate()
        ReviewTask(id="r1", task_id="t1", question="Which candidate is correct?").validate()


if __name__ == "__main__":
    unittest.main()
