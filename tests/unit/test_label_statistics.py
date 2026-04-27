import unittest

from app.research.bootstrap_contracts import BootstrapSample, BootstrapSpan
from app.research.label_statistics import build_label_statistics, label_statistics_to_dict, tokenize_with_offsets


class TestLabelStatistics(unittest.TestCase):
    def test_tokenize_with_offsets(self):
        tokens = tokenize_with_offsets("Heart failure.")

        self.assertEqual(tokens[0].token, "heart")
        self.assertEqual(tokens[0].start, 0)
        self.assertEqual(tokens[1].token, "failure")

    def test_build_entity_context_other_stats(self):
        sample = BootstrapSample(
            id="s1",
            text="risk of heart failure rises",
            spans=(BootstrapSpan(start=8, end=21, text="heart failure", label="Term"),),
        )
        stats = build_label_statistics([sample], context_window=1)

        self.assertEqual(stats["heart"].entity_count, 1)
        self.assertEqual(stats["of"].context_count, 1)
        self.assertEqual(stats["risk"].other_count, 1)

    def test_statistics_to_dict_contains_probabilities(self):
        sample = BootstrapSample(
            id="s1",
            text="heart failure",
            spans=(BootstrapSpan(start=0, end=13, text="heart failure", label="Term"),),
        )
        row = label_statistics_to_dict(build_label_statistics([sample]))["heart"]

        self.assertEqual(row["entity_probability"], 1.0)
        self.assertEqual(row["total"], 1)


if __name__ == "__main__":
    unittest.main()
