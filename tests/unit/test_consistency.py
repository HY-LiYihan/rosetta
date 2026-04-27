import unittest

from app.research.bootstrap_contracts import BootstrapCandidate, BootstrapSpan
from app.research.consistency import (
    score_candidate_consistency,
    score_candidate_groups,
    span_f1,
)


def _candidate(sample_id, candidate_id, spans, confidence=None):
    return BootstrapCandidate(
        sample_id=sample_id,
        candidate_id=candidate_id,
        annotation_markup="",
        spans=tuple(spans),
        model_confidence=confidence,
    )


class TestSpanF1(unittest.TestCase):
    def test_empty_is_perfect(self):
        self.assertEqual(span_f1((), ()), 1.0)

    def test_partial_overlap(self):
        left = (
            BootstrapSpan(start=0, end=4, text="term", label="T"),
            BootstrapSpan(start=5, end=9, text="test", label="T"),
        )
        right = (
            BootstrapSpan(start=0, end=4, text="term", label="T"),
            BootstrapSpan(start=10, end=14, text="word", label="T"),
        )
        self.assertEqual(span_f1(left, right), 0.5)


class TestConsistencyScore(unittest.TestCase):
    def test_high_route_for_identical_candidates(self):
        span = BootstrapSpan(start=0, end=4, text="term", label="T")
        score = score_candidate_consistency(
            "s1",
            [
                _candidate("s1", "c1", [span], 0.9),
                _candidate("s1", "c2", [span], 0.8),
            ],
        )

        self.assertEqual(score.route, "high")
        self.assertEqual(score.pairwise_span_f1, 1.0)
        self.assertEqual(score.exact_match_rate, 1.0)
        self.assertEqual(score.average_model_confidence, 0.85)

    def test_low_route_for_disagreement(self):
        score = score_candidate_consistency(
            "s1",
            [
                _candidate("s1", "c1", [BootstrapSpan(start=0, end=4, text="term", label="T")], 0.6),
                _candidate("s1", "c2", [BootstrapSpan(start=5, end=9, text="test", label="T")], 0.6),
            ],
        )

        self.assertEqual(score.route, "low")
        self.assertEqual(score.pairwise_span_f1, 0.0)
        self.assertGreater(score.uncertainty_score, 0.0)

    def test_medium_route_for_partial_overlap(self):
        common = BootstrapSpan(start=0, end=4, text="term", label="T")
        score = score_candidate_consistency(
            "s1",
            [
                _candidate("s1", "c1", [common, BootstrapSpan(start=5, end=9, text="test", label="T")]),
                _candidate("s1", "c2", [common]),
            ],
            medium_threshold=0.5,
        )

        self.assertEqual(score.route, "medium")

    def test_group_scores_sorted_by_sample_id(self):
        scores = score_candidate_groups(
            [
                _candidate("s2", "c1", []),
                _candidate("s1", "c1", []),
            ]
        )

        self.assertEqual([score.sample_id for score in scores], ["s1", "s2"])


if __name__ == "__main__":
    unittest.main()
