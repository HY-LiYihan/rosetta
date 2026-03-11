import unittest

from app.domain.annotation_format import extract_annotation_tokens, validate_annotation_markup


class TestAnnotationFormat(unittest.TestCase):
    def test_validate_visible_and_implicit(self):
        ok, reason = validate_annotation_markup("[supper]{nominalization} [!主语省略]{reference}")
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_reject_legacy_parentheses(self):
        ok, reason = validate_annotation_markup("[supper](nominalization)")
        self.assertFalse(ok)
        self.assertIn("旧格式", reason)

    def test_extract_tokens(self):
        tokens = extract_annotation_tokens("[x]{a} [!y]{b}")
        self.assertEqual(len(tokens), 2)
        self.assertFalse(tokens[0]["implicit"])
        self.assertTrue(tokens[1]["implicit"])
        self.assertEqual(tokens[1]["text"], "y")


if __name__ == "__main__":
    unittest.main()
