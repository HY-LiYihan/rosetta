import unittest

from app.research.contracts import ConflictRule
from app.research.verifier import verify_annotation_result


class TestResearchVerifier(unittest.TestCase):
    def test_verify_annotation_result_detects_span_and_logic_conflict(self):
        issues = verify_annotation_result(
            sample_text="She said hello.",
            parsed_result={
                "text": "She said hello.",
                "annotation": "[reported]{projection} [hello]{background}",
                "explanation": "demo",
            },
            conflict_rules=(
                ConflictRule(
                    name="projection-vs-background",
                    labels=("projection", "background"),
                    message="mutually exclusive",
                ),
            ),
        )
        codes = {issue.code for issue in issues}
        self.assertIn("span_not_found", codes)
        self.assertIn("logic_conflict", codes)


if __name__ == "__main__":
    unittest.main()
