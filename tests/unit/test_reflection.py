import unittest

from app.research.bootstrap_contracts import BootstrapCandidate, BootstrapSample, BootstrapSpan
from app.research.label_statistics import build_label_statistics
from app.research.reflection import build_reflection_plan, reflection_plan_to_dict


class TestReflectionPlan(unittest.TestCase):
    def test_flags_possible_false_negative(self):
        gold = BootstrapSample(
            id="gold",
            text="heart failure",
            spans=(BootstrapSpan(start=0, end=13, text="heart failure", label="Term"),),
        )
        sample = BootstrapSample(id="s1", text="heart failure", spans=())
        candidate = BootstrapCandidate(sample_id="s1", candidate_id="c1", annotation_markup="", spans=())
        plan = build_reflection_plan(sample, candidate, build_label_statistics([gold]), entity_threshold=0.5)

        self.assertEqual(plan.items[0].item_type, "possible_false_negative")
        self.assertEqual(plan.items[0].token, "heart")

    def test_flags_unseen_token(self):
        sample = BootstrapSample(id="s1", text="novelterm appears", spans=())
        candidate = BootstrapCandidate(sample_id="s1", candidate_id="c1", annotation_markup="", spans=())
        plan = build_reflection_plan(sample, candidate, stats={})

        self.assertEqual(plan.items[0].item_type, "unseen_token")

    def test_plan_to_dict(self):
        sample = BootstrapSample(id="s1", text="novelterm", spans=())
        candidate = BootstrapCandidate(sample_id="s1", candidate_id="c1", annotation_markup="", spans=())
        row = reflection_plan_to_dict(build_reflection_plan(sample, candidate, stats={}))

        self.assertEqual(row["sample_id"], "s1")
        self.assertEqual(row["candidate_id"], "c1")
        self.assertEqual(row["items"][0]["item_type"], "unseen_token")


if __name__ == "__main__":
    unittest.main()
