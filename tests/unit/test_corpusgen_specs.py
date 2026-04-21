import unittest

from app.corpusgen.specs import load_corpus_spec


class TestCorpusSpec(unittest.TestCase):
    def test_load_spec_template(self):
        spec = load_corpus_spec("configs/corpusgen/domain/linguistics_zh_qa.json")
        self.assertEqual(spec.name, "linguistics-zh-qa")
        self.assertEqual(spec.model, "glm-5")
        self.assertEqual(spec.embedding_model, "embedding-3")
        self.assertEqual(spec.task_count, 4)
        self.assertEqual(spec.target_schema, "qa")


if __name__ == "__main__":
    unittest.main()
