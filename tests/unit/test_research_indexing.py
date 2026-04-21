import tempfile
import unittest

from app.research.config import parse_research_config
from app.research.indexing import build_example_index, query_example_index


class TestResearchIndexing(unittest.TestCase):
    def test_build_and_query_cpu_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = parse_research_config(
                {
                    "name": "demo",
                    "platform": "zhipuai",
                    "model": "glm-5",
                    "api_key_env": "ZHIPUAI_API_KEY",
                    "definition": "Projection definition",
                    "retrieval_strategy": "embedding",
                    "embedding_model": "embedding-3",
                    "embedding_dimensions": 3,
                    "index_dir": tmp,
                    "canonical_examples": [
                        {
                            "id": "ex-1",
                            "text": "She said hello.",
                            "annotation": "[said]{projection} hello.",
                            "explanation": "speech process",
                        },
                        {
                            "id": "ex-2",
                            "text": "The sky is blue.",
                            "annotation": "[sky]{background} is blue.",
                            "explanation": "background statement",
                        },
                    ],
                }
            )

            lookup = {
                "She said hello.\nspeech process": [1.0, 0.0, 0.0],
                "The sky is blue.\nbackground statement": [0.0, 1.0, 0.0],
                "She said the project was delayed.": [0.9, 0.1, 0.0],
            }

            def fake_embedder(_config, texts):
                return [lookup[text] for text in texts]

            manifest = build_example_index(config, embedder=fake_embedder)
            self.assertEqual(manifest["example_count"], 2)
            self.assertEqual(manifest["dimension"], 3)

            ranked = query_example_index(
                config,
                "She said the project was delayed.",
                embedder=fake_embedder,
            )
            self.assertEqual(ranked[0][0], "ex-1")


if __name__ == "__main__":
    unittest.main()
