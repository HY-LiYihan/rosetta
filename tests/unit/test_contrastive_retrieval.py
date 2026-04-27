import unittest

from app.research.bootstrap_contracts import BootstrapSample, BootstrapSpan
from app.research.contrastive_retrieval import (
    contrastive_selection_to_dict,
    lexical_similarity,
    select_contrastive_examples,
)


def _sample(sample_id, text):
    return BootstrapSample(
        id=sample_id,
        text=text,
        spans=(BootstrapSpan(start=0, end=1, text=text[:1], label="X"),) if text else (),
    )


class TestContrastiveRetrieval(unittest.TestCase):
    def test_lexical_similarity(self):
        self.assertEqual(lexical_similarity("heart failure care", "heart failure treatment"), 0.5)

    def test_selects_similar_and_boundary_examples(self):
        query = _sample("q", "heart failure treatment")
        examples = [
            _sample("near", "heart failure care"),
            _sample("mid", "heart disease"),
            _sample("far", "wind turbine blade"),
        ]
        selection = select_contrastive_examples(query, examples, similar_k=1, boundary_k=1)

        self.assertEqual(selection.similar[0].sample_id, "near")
        self.assertEqual(selection.boundary[0].sample_id, "far")

    def test_excludes_query_from_examples(self):
        query = _sample("q", "same text")
        selection = select_contrastive_examples(query, [query, _sample("x", "same text")], similar_k=2)

        self.assertEqual([hit.sample_id for hit in selection.similar], ["x"])

    def test_selection_to_dict(self):
        query = _sample("q", "heart failure")
        selection = select_contrastive_examples(query, [_sample("x", "heart care")], similar_k=1, boundary_k=0)
        row = contrastive_selection_to_dict(selection)

        self.assertEqual(row["query_id"], "q")
        self.assertEqual(row["similar"][0]["sample_id"], "x")
        self.assertIn("sample", row["similar"][0])


if __name__ == "__main__":
    unittest.main()
