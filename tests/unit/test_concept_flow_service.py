import unittest

from app.services.concept_flow_service import (
    apply_import,
    create_concept_if_valid,
    parse_and_preview_import,
)


class TestConceptFlowService(unittest.TestCase):
    def test_parse_and_preview_import_success(self):
        existing = []
        content = (
            '{"version":"1.0","concepts":[{"name":"A","prompt":"p","examples":[],"category":"c","is_default":false}]}'
        )
        result = parse_and_preview_import(content, existing)
        self.assertTrue(result["ok"])
        self.assertEqual(result["preview"]["concept_count"], 1)

    def test_create_concept_if_valid_duplicate(self):
        ok, message, concept = create_concept_if_valid(
            existing_concepts=[{"name": "A"}],
            name="A",
            prompt="p",
            category="c",
        )
        self.assertFalse(ok)
        self.assertIn("已存在", message)
        self.assertIsNone(concept)

    def test_apply_import_replace(self):
        preview = {
            "version": "1.1",
            "normalized_concepts": [{"name": "N", "prompt": "p", "examples": [], "category": "c", "is_default": False}],
        }
        concepts, msg, version = apply_import([], preview, "替换现有概念")
        self.assertEqual(version, "1.1")
        self.assertEqual(len(concepts), 1)
        self.assertIn("成功替换", msg)


if __name__ == "__main__":
    unittest.main()
