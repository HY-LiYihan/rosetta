import unittest

from app.ui.viewmodels.home_viewmodel import build_home_metrics


class TestHomeViewModel(unittest.TestCase):
    def test_build_home_metrics(self):
        concepts = [
            {"name": "默认", "is_default": True},
            {"name": "X", "is_default": False},
        ]
        history = [
            {"annotation": "abc"},
            {"annotation": "abcdef"},
        ]
        metrics = build_home_metrics(concepts, history)
        self.assertEqual(metrics["concept_count"], 2)
        self.assertEqual(metrics["custom_count"], 1)
        self.assertEqual(metrics["history_count"], 2)
        self.assertAlmostEqual(metrics["avg_length"], 4.5)


if __name__ == "__main__":
    unittest.main()
