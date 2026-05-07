import unittest
from datetime import datetime

from app.services.annotation_service import (
    annotation_assistant_system_prompt,
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
        self.assertIn("请根据以下概念定义标注文本。", prompt)
        self.assertIn("概念定义：\ndefinition", prompt)
        self.assertIn("相似参考样例（可选，只用于理解边界，不是当前文本答案）：", prompt)
        self.assertIn("标注格式：", prompt)
        self.assertIn("通用格式示例（只说明输出格式，不代表当前任务概念）：", prompt)
        self.assertIn("待标注文本：\ninput text", prompt)
        self.assertIn("任务强调：", prompt)
        self.assertIn('"text": "Example source text."', prompt)
        self.assertIn("annotation", prompt)
        self.assertNotIn("不要参考金答案", prompt)

    def test_build_annotation_prompt_uses_concept_neutral_protocol_example(self):
        concept = {
            "name": "demo",
            "prompt": "Mark ACTER terms.",
            "examples": [{"text": "Corruption ?", "annotation": "[Corruption]{Term}", "explanation": "gold"}],
        }
        prompt = build_annotation_prompt(concept, "Not in our company …")

        self.assertIn('"text": "Example source text."', prompt)
        self.assertIn("[Example]{Term}", prompt)
        self.assertNotIn('"text": "Corruption ?"', prompt)
        self.assertNotIn("[Corruption]{Term}", prompt)
        self.assertIn("待标注文本：\nNot in our company …", prompt)

    def test_build_annotation_prompt_injects_explicit_reference_examples(self):
        concept = {
            "name": "demo",
            "prompt": "Mark domain terms.",
            "examples": [{"text": "Gold label source", "annotation": "[Gold label source]{Term}", "explanation": "label inference"}],
            "reference_examples": [
                {
                    "text": "Similar source text",
                    "annotation": "[Similar source text]{Term}",
                    "explanation": "retrieved boundary reference",
                    "similarity": 0.91,
                }
            ],
        }
        prompt = build_annotation_prompt(concept, "Current source text")

        self.assertIn("相似参考样例（可选，只用于理解边界，不是当前文本答案）：", prompt)
        self.assertIn("参考样例 1，相似度 0.91：", prompt)
        self.assertIn("原文：Similar source text", prompt)
        self.assertIn("标准 annotation：[Similar source text]{Term}", prompt)
        self.assertIn("待标注文本：\nCurrent source text", prompt)
        self.assertNotIn("Gold label source", prompt)

    def test_build_annotation_prompt_can_request_full_json_protocol(self):
        concept = {
            "name": "demo",
            "prompt": "definition",
            "examples": [],
            "output_format": "rosetta.annotation_doc.v3.1.full_json",
        }
        prompt = build_annotation_prompt(concept, "input text")

        self.assertIn("完整 AnnotationDoc JSON object", prompt)
        self.assertIn("relations", prompt)
        self.assertNotIn("必须使用 [原文]{概念标签} 格式", prompt)
        self.assertIn("通用格式示例（只说明输出格式，不代表当前任务概念）：", prompt)

    def test_build_annotation_prompt_can_use_english_prompt_contract(self):
        concept = {
            "name": "demo",
            "prompt": "Mark domain terms.",
            "examples": [{"text": "a", "annotation": "[a]{Term}", "explanation": "c"}],
            "reference_examples": [{"text": "Similar text", "annotation": "[Similar text]{Term}", "similarity": 0.9}],
            "prompt_language": "en-US",
        }

        prompt = build_annotation_prompt(concept, "input text")

        self.assertEqual(
            annotation_assistant_system_prompt("en-US"),
            "You are a rigorous annotation assistant. Output JSON only.",
        )
        self.assertIn("Annotate the text according to the concept definition.", prompt)
        self.assertIn("Concept definition:\nMark domain terms.", prompt)
        self.assertIn("Similar reference examples", prompt)
        self.assertIn("Reference example 1, similarity 0.9:", prompt)
        self.assertIn("Annotation format:", prompt)
        self.assertIn("Generic format example", prompt)
        self.assertIn("Text to annotate:\ninput text", prompt)
        self.assertIn("Task emphasis:", prompt)

    def test_parse_annotation_response_json_code_block(self):
        raw = """```json\n{\"text\":\"t\",\"annotation\":\"[t]{demo}\",\"explanation\":\"e\"}\n```"""
        parsed, warning = parse_annotation_response(raw)
        self.assertIsNone(warning)
        self.assertEqual(parsed["text"], "t")

    def test_parse_annotation_response_accepts_full_annotation_doc(self):
        raw = """{
          "text": "heart failure",
          "annotation": {
            "version": "3.1",
            "text": "heart failure",
            "layers": {
              "spans": [
                {"id": "s1", "start": 0, "end": 13, "text": "heart failure", "label": "Term", "implicit": false}
              ],
              "relations": [],
              "attributes": [],
              "comments": [],
              "document_labels": []
            }
          },
          "explanation": "e"
        }"""
        parsed, warning = parse_annotation_response(raw)

        self.assertIsNone(warning)
        self.assertEqual(parsed["annotation"]["layers"]["spans"][0]["label"], "Term")

    def test_parse_annotation_response_accepts_empty_annotation_for_no_spans(self):
        raw = """{"text":"ordinary sentence","annotation":"","explanation":"no target spans"}"""
        parsed, warning = parse_annotation_response(raw)

        self.assertIsNone(warning)
        self.assertEqual(parsed["annotation"]["layers"]["spans"], [])

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
