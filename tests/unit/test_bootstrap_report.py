import unittest

from app.research.bootstrap_report import build_bootstrap_report
from app.research.consistency import ConsistencyScore
from app.research.label_statistics import TokenLabelStat


class TestBootstrapReport(unittest.TestCase):
    def test_build_report_contains_core_sections(self):
        report = build_bootstrap_report(
            manifest={
                "run_name": "unit",
                "sample_count": 2,
                "candidate_count": 4,
                "review_task_count": 1,
                "reflection_plan_count": 1,
            },
            scores=[
                ConsistencyScore(
                    sample_id="s1",
                    candidate_count=2,
                    pairwise_span_f1=1.0,
                    exact_match_rate=1.0,
                    average_model_confidence=0.9,
                    uncertainty_score=0.0,
                    route="high",
                )
            ],
            review_queue=[],
            label_stats={"term": TokenLabelStat(token="term", entity_count=2)},
            reflection_plans=[],
            experiment={"name": "exp", "baselines": ["zero_shot"], "metrics": ["span_f1"]},
        )

        self.assertIn("# Concept Bootstrap Report", report)
        self.assertIn("## Consistency Routes", report)
        self.assertIn("`zero_shot`", report)
        self.assertIn("`span_f1`", report)


if __name__ == "__main__":
    unittest.main()
