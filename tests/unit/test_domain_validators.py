import unittest

from app.domain.validators import ImportValidationError, normalize_payload
from app.services.concept_service import validate_import_payload


class TestDomainValidators(unittest.TestCase):
    def test_accepts_legacy_payload_without_version(self):
        payload = {
            "concepts": [
                {
                    "name": "c1",
                    "prompt": "p1",
                    "examples": [{"text": "t", "annotation": "a"}],
                    "category": "cat",
                    "is_default": False,
                }
            ]
        }

        normalized = normalize_payload(payload)
        self.assertIn("version", normalized)
        self.assertEqual(normalized["concepts"][0]["examples"][0]["explanation"], "")

    def test_rejects_missing_required_field(self):
        payload = {
            "concepts": [
                {
                    "name": "c1",
                    "prompt": "p1",
                    "examples": [{"text": "t", "annotation": "a"}],
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
                    "examples": [{"text": "t"}],
                    "category": "cat",
                    "is_default": False,
                }
            ]
        }

        is_valid, error = validate_import_payload(payload)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertEqual(error["field"], "concepts[0].examples[0].annotation")


if __name__ == "__main__":
    unittest.main()
