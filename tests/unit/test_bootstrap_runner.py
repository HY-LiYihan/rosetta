import json
import tempfile
import unittest
from pathlib import Path

from app.research.bootstrap_runner import run_bootstrap_analysis


class TestBootstrapRunner(unittest.TestCase):
    def test_run_bootstrap_analysis_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            samples = tmp_path / "samples.jsonl"
            candidates = tmp_path / "candidates.jsonl"
            output = tmp_path / "out"

            samples.write_text(
                json.dumps(
                    {
                        "id": "s1",
                        "text": "heart failure",
                        "spans": [{"start": 0, "end": 13, "text": "heart failure", "label": "Term"}],
                    }
                )
                + "\n"
                + json.dumps({"id": "s2", "text": "heart disease", "spans": []})
                + "\n",
                encoding="utf-8",
            )
            candidates.write_text(
                json.dumps(
                    {
                        "sample_id": "s2",
                        "candidate_id": "c1",
                        "text": "heart disease",
                        "annotation_markup": "[heart]{Term}",
                        "model_confidence": 0.6,
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "sample_id": "s2",
                        "candidate_id": "c2",
                        "text": "heart disease",
                        "annotation_markup": "[disease]{Term}",
                        "model_confidence": 0.6,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            manifest = run_bootstrap_analysis(samples, candidates, output_dir=output, run_name="unit")
            run_dir = Path(manifest["output_dir"])

            self.assertTrue((run_dir / "manifest.json").exists())
            self.assertTrue((run_dir / "report.md").exists())
            self.assertTrue((run_dir / "consistency_scores.jsonl").exists())
            self.assertTrue((run_dir / "human_review_queue.jsonl").exists())
            self.assertGreater(manifest["review_task_count"], 0)


if __name__ == "__main__":
    unittest.main()
