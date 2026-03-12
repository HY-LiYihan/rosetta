import unittest
from datetime import datetime

from app.services.annotation_service import (
    build_annotation_prompt,
    build_history_export_filename,
    build_history_export_json,
    parse_annotation_response,
)


class TestAnnotationService(unittest.TestCase):
    def test_build_annotation_prompt_contains_required_keys(self):
        concept = {
            "name": "demo",
            "prompt": "definition",
            "examples": [{"text": "a", "annotation": "[a]{demo}", "explanation": "c"}],
        }
        prompt = build_annotation_prompt(concept, "input text")
        self.assertIn("概念：demo", prompt)
        self.assertIn('"text": "input text"', prompt)
        self.assertIn("annotation", prompt)

    def test_parse_annotation_response_json_code_block(self):
        raw = """```json\n{\"text\":\"t\",\"annotation\":\"[t]{demo}\",\"explanation\":\"e\"}\n```"""
        parsed, warning = parse_annotation_response(raw)
        self.assertIsNone(warning)
        self.assertEqual(parsed["text"], "t")

    def test_parse_annotation_response_missing_fields(self):
        raw = "{\"text\":\"t\"}"
        parsed, warning = parse_annotation_response(raw)
        self.assertIsNone(parsed)
        self.assertIn("缺少必需字段", warning)

    def test_build_history_export_filename(self):
        fixed = datetime(2026, 3, 12, 9, 8, 7)
        filename = build_history_export_filename(now=fixed)
        self.assertEqual(filename, "annotation_history_20260312_090807.json")

    def test_build_history_export_json(self):
        fixed = datetime(2026, 3, 12, 9, 8, 7)
        history = [{"timestamp": "2026-03-11 10:00:00", "concept": "demo"}]
        payload = build_history_export_json(history, now=fixed)
        self.assertIn('"exported_at": "2026-03-12 09:08:07"', payload)
        self.assertIn('"history_count": 1', payload)
        self.assertIn('"concept": "demo"', payload)


if __name__ == "__main__":
    unittest.main()
