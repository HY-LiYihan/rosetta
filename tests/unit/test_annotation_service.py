import unittest

from app.services.annotation_service import (
    build_annotation_prompt,
    parse_annotation_response,
)


class TestAnnotationService(unittest.TestCase):
    def test_build_annotation_prompt_contains_required_keys(self):
        concept = {
            "name": "demo",
            "prompt": "definition",
            "examples": [{"text": "a", "annotation": "b", "explanation": "c"}],
        }
        prompt = build_annotation_prompt(concept, "input text")
        self.assertIn("概念：demo", prompt)
        self.assertIn('"text": "input text"', prompt)
        self.assertIn("annotation", prompt)

    def test_parse_annotation_response_json_code_block(self):
        raw = """```json\n{\"text\":\"t\",\"annotation\":\"a\",\"explanation\":\"e\"}\n```"""
        parsed, warning = parse_annotation_response(raw)
        self.assertIsNone(warning)
        self.assertEqual(parsed["text"], "t")

    def test_parse_annotation_response_missing_fields(self):
        raw = "{\"text\":\"t\"}"
        parsed, warning = parse_annotation_response(raw)
        self.assertIsNone(parsed)
        self.assertIn("缺少必需字段", warning)


if __name__ == "__main__":
    unittest.main()
