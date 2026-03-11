import unittest

from app.services.concept_service import build_import_preview, merge_concepts


class TestImportFlow(unittest.TestCase):
    def test_preview_then_merge_flow(self):
        existing = [
            {
                "name": "c1",
                "prompt": "p1",
                "examples": [],
                "category": "cat",
                "is_default": False,
            }
        ]

        payload = {
            "concepts": [
                {
                    "name": "c1",
                    "prompt": "p1",
                    "examples": [{"text": "a", "annotation": "b"}],
                    "category": "cat",
                    "is_default": False,
                },
                {
                    "name": "c2",
                    "prompt": "p2",
                    "examples": [{"text": "x", "annotation": "y"}],
                    "category": "cat",
                    "is_default": False,
                },
            ]
        }

        ok, err, preview = build_import_preview(payload, existing)
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertEqual(preview["duplicate_count"], 1)

        merged, _ = merge_concepts(existing, preview["normalized_concepts"])
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[1]["name"], "c2")


if __name__ == "__main__":
    unittest.main()
