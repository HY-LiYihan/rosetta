import tempfile
import unittest
from pathlib import Path

from app.research.runner import preview_prompt, run_pipeline


class TestResearchRunner(unittest.TestCase):
    def test_preview_prompt_returns_selected_examples(self):
        result = preview_prompt(
            config_path="configs/research/pilot_template.json",
            dataset_path="configs/research/pilot_dataset.example.jsonl",
        )
        self.assertEqual(result["config_name"], "projection-pilot")
        self.assertTrue(result["retrieved_examples"])
        self.assertIn("待标注样本", result["prompt"])

    def test_run_pipeline_audit_exports_conflicts(self):
        def fake_predictor(config, prompt):
            return '{"text":"She said that the results were surprising.","annotation":"[said]{background} that the results were surprising.","explanation":"wrong label"}'

        with tempfile.TemporaryDirectory() as tmp:
            manifest = run_pipeline(
                config_path="configs/research/pilot_template.json",
                dataset_path="configs/research/pilot_dataset.example.jsonl",
                mode="audit",
                output_dir=tmp,
                limit=1,
                predictor=fake_predictor,
            )
            self.assertEqual(manifest["sample_count"], 1)
            self.assertEqual(manifest["conflict_count"], 1)
            conflict_path = Path(manifest["output_dir"]) / "conflicts.jsonl"
            self.assertTrue(conflict_path.exists())


if __name__ == "__main__":
    unittest.main()
