import unittest

import numpy as np

from app.infrastructure.embedding import (
    LocalEmbeddingProfile,
    LocalHashingEmbedder,
    embedding_similarity,
    rank_texts,
)
from app.workflows.bootstrap.guideline import _reference_examples_for_task


class TestLocalEmbedding(unittest.TestCase):
    def test_hash_embedding_is_stable_and_normalized(self):
        embedder = LocalHashingEmbedder(LocalEmbeddingProfile(dimensions=64))

        first = embedder.embed("electrochemical catalyst improves reaction rate")
        second = embedder.embed("electrochemical catalyst improves reaction rate")

        self.assertEqual(first.shape, (64,))
        self.assertTrue(np.allclose(first, second))
        self.assertAlmostEqual(float(np.linalg.norm(first)), 1.0, places=5)

    def test_rank_texts_uses_local_embedding_similarity(self):
        documents = [
            {"id": "chem", "text": "electrochemistry catalysts accelerate reactions"},
            {"id": "astro", "text": "galaxies and stellar spectra are observed"},
            {"id": "policy", "text": "public procurement policy changes"},
        ]

        hits = rank_texts("electrochemical catalysis reaction", documents)

        self.assertEqual(hits[0].id, "chem")
        self.assertGreater(hits[0].score, hits[-1].score)

    def test_embedding_similarity_is_not_plain_token_jaccard(self):
        score = embedding_similarity("electrochemical catalysis", "electrochemistry catalyst")

        self.assertGreater(score, 0.0)

    def test_reference_examples_use_local_embedding_model_marker(self):
        prediction_inputs = [
            ("target", {"id": "target", "text": "electrochemical catalysis improves battery reactions", "spans": []}),
            (
                "near",
                {
                    "id": "near",
                    "text": "electrochemistry catalysts improve battery reaction speed",
                    "spans": [{"start": 0, "end": 28, "text": "electrochemistry catalysts", "label": "Term"}],
                },
            ),
            (
                "far",
                {
                    "id": "far",
                    "text": "public procurement policy changed in the city",
                    "spans": [{"start": 7, "end": 18, "text": "procurement", "label": "Term"}],
                },
            ),
        ]

        examples = _reference_examples_for_task(None, prediction_inputs, "target", prediction_inputs[0][1], 1)

        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]["id"], "near")
        self.assertEqual(examples[0]["retrieval_model"], "rosetta-local-hash-384")


if __name__ == "__main__":
    unittest.main()
