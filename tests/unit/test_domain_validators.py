import unittest

from app.domain.validators import normalize_payload


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

        with self.assertRaises(ValueError):
            normalize_payload(payload)


if __name__ == "__main__":
    unittest.main()
