import unittest
from datetime import datetime

from app.domain.validators import ImportValidationError, normalize_payload
from app.services.concept_service import (
    build_export_filename,
    build_import_preview,
    validate_import_payload,
)


class TestDomainValidators(unittest.TestCase):
    def test_accepts_legacy_payload_without_version(self):
        payload = {
            "concepts": [
                {
                    "name": "c1",
                    "prompt": "p1",
                    "examples": [{"text": "t", "annotation": "[t]{demo}", "explanation": "说明"}],
                    "category": "cat",
                    "is_default": False,
                }
            ]
        }

        normalized = normalize_payload(payload)
        self.assertIn("version", normalized)
        self.assertEqual(normalized["concepts"][0]["examples"][0]["explanation"], "说明")

    def test_rejects_missing_required_field(self):
        payload = {
            "concepts": [
                {
                    "name": "c1",
                    "prompt": "p1",
                    "examples": [{"text": "t", "annotation": "[t]{demo}", "explanation": "说明"}],
                    "category": "cat",
                }
            ]
        }

        with self.assertRaises(ImportValidationError) as ctx:
            normalize_payload(payload)
        self.assertIn("concepts[0].is_default", str(ctx.exception))

    def test_validate_payload_returns_structured_error(self):
        payload = {
            "concepts": [
                {
                    "name": "c1",
                    "prompt": "p1",
                    "examples": [{"text": "t", "annotation": "[t]{demo}", "explanation": ""}],
                    "category": "cat",
                    "is_default": False,
                }
            ]
        }

        is_valid, error = validate_import_payload(payload)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertEqual(error["field"], "concepts[0].examples[0].explanation")

    def test_import_preview_counts_duplicates_and_auto_fixes(self):
        payload = {
            "concepts": [
                {
                    "name": "c1",
                    "prompt": "p1",
                    "examples": [{"text": "t", "annotation": "[t]{demo}", "explanation": "说明"}],
                    "category": "cat",
                    "is_default": False,
                },
                {
                    "name": "c2",
                    "prompt": "p2",
                    "examples": [{"text": "t2", "annotation": "[!隐含义]{demo}", "explanation": "说明2"}],
                    "category": "cat",
                    "is_default": False,
                },
            ]
        }
        existing = [{"name": "c1"}]

        ok, error, preview = build_import_preview(payload, existing)
        self.assertTrue(ok)
        self.assertIsNone(error)
        self.assertEqual(preview["duplicate_count"], 1)
        self.assertEqual(preview["auto_fix_count"], 0)

    def test_export_filename_contains_version_and_date(self):
        file_name = build_export_filename(version="1.2", now=datetime(2026, 3, 10))
        self.assertEqual(file_name, "concepts_v1_2_20260310.json")


if __name__ == "__main__":
    unittest.main()
