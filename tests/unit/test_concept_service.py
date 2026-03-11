import unittest

from app.services.concept_service import (
    build_export_json,
    merge_concepts,
    replace_concepts,
)


class TestConceptService(unittest.TestCase):
    def test_build_export_json_contains_version(self):
        payload = build_export_json([])
        self.assertIn('"version"', payload)
        self.assertIn('"concepts"', payload)

    def test_replace_concepts_normalizes_examples(self):
        concepts, _ = replace_concepts([
            {
                "name": "c",
                "prompt": "p",
                "examples": [{"text": "t", "annotation": "[t]{demo}", "explanation": "说明"}],
                "category": "cat",
                "is_default": False,
            }
        ])
        self.assertEqual(concepts[0]["examples"][0]["explanation"], "说明")

    def test_merge_concepts_skips_duplicates(self):
        existing = [
            {
                "name": "same",
                "prompt": "p",
                "examples": [],
                "category": "cat",
                "is_default": False,
            }
        ]
        merged, msg = merge_concepts(
            existing,
            [
                {
                    "name": "same",
                    "prompt": "p",
                    "examples": [],
                    "category": "cat",
                    "is_default": False,
                },
                {
                    "name": "new",
                    "prompt": "p2",
                    "examples": [],
                    "category": "cat",
                    "is_default": False,
                },
            ],
        )
        self.assertEqual(len(merged), 2)
        self.assertIn("跳过了 1 个重复概念", msg)


if __name__ == "__main__":
    unittest.main()
