import unittest

from app.research.bootstrap_contracts import BootstrapCandidate, BootstrapSpan
from app.research.consistency import score_candidate_groups
from app.research.human_review import (
    MANUAL_OPTION_ID,
    build_human_review_queue,
    candidate_bundle_for_review,
    human_review_task_to_dict,
)


def _candidate(sample_id, candidate_id, start, text="term"):
    return BootstrapCandidate(
        sample_id=sample_id,
        candidate_id=candidate_id,
        annotation_markup=f"[{text}]{{T}}",
        spans=(BootstrapSpan(start=start, end=start + len(text), text=text, label="T"),),
        explanation=f"{candidate_id} explanation",
        model_confidence=0.5,
    )


class TestHumanReviewQueue(unittest.TestCase):
    def test_builds_review_task_for_low_route(self):
        candidates = [_candidate("s1", "c2", 5), _candidate("s1", "c1", 0)]
        scores = score_candidate_groups(candidates)
        queue = build_human_review_queue(candidates, scores)

        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0].sample_id, "s1")
        self.assertEqual(queue[0].route, "low")
        self.assertEqual([option.candidate_id for option in queue[0].options], ["c1", "c2"])
        self.assertEqual(queue[0].manual_option_id, MANUAL_OPTION_ID)

    def test_skips_high_route_by_default(self):
        span = BootstrapSpan(start=0, end=4, text="term", label="T")
        candidates = [
            BootstrapCandidate(sample_id="s1", candidate_id="c1", annotation_markup="", spans=(span,), model_confidence=0.9),
            BootstrapCandidate(sample_id="s1", candidate_id="c2", annotation_markup="", spans=(span,), model_confidence=0.9),
        ]
        scores = score_candidate_groups(candidates)
        queue = build_human_review_queue(candidates, scores)

        self.assertEqual(queue, [])

    def test_task_to_dict(self):
        candidates = [_candidate("s1", "c1", 0), _candidate("s1", "c2", 5)]
        task = build_human_review_queue(candidates, score_candidate_groups(candidates))[0]
        row = human_review_task_to_dict(task)

        self.assertEqual(row["manual_option_id"], MANUAL_OPTION_ID)
        self.assertEqual(row["options"][0]["option_id"], "A")

    def test_candidate_bundle_sorted(self):
        bundle = candidate_bundle_for_review([_candidate("s1", "c2", 5), _candidate("s1", "c1", 0)])

        self.assertEqual([row["candidate_id"] for row in bundle], ["c1", "c2"])


if __name__ == "__main__":
    unittest.main()
