import tempfile
import unittest
from pathlib import Path

from app.research.bootstrap_contracts import BootstrapDataError, BootstrapSample, BootstrapSpan
from app.research.bootstrap_io import (
    candidate_from_dict,
    read_samples_jsonl,
    sample_from_dict,
    sample_to_dict,
    spans_from_markup,
    write_samples_jsonl,
)


class TestBootstrapSpans(unittest.TestCase):
    def test_parse_markup_to_offsets(self):
        spans = spans_from_markup("Patients with heart failure improved.", "[heart failure]{Specific_Term}")

        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].start, 14)
        self.assertEqual(spans[0].end, 27)
        self.assertEqual(spans[0].label, "Specific_Term")

    def test_reject_bad_offsets(self):
        with self.assertRaises(BootstrapDataError):
            sample_from_dict(
                {
                    "id": "bad",
                    "text": "abc",
                    "spans": [{"start": 0, "end": 2, "text": "bc", "label": "X"}],
                }
            )


class TestBootstrapSamples(unittest.TestCase):
    def test_sample_accepts_span_jsonl(self):
        sample = sample_from_dict(
            {
                "id": "s1",
                "text": "wind energy grows",
                "spans": [{"start": 0, "end": 11, "text": "wind energy", "label": "Specific_Term"}],
                "metadata": {"dataset": "ACTER"},
            }
        )

        self.assertEqual(sample.id, "s1")
        self.assertEqual(sample.metadata["dataset"], "ACTER")
        self.assertEqual(sample.spans[0].text, "wind energy")

    def test_sample_accepts_legacy_gold_annotation_but_outputs_spans(self):
        sample = sample_from_dict({"id": "s1", "text": "heart failure", "gold_annotation": "[heart failure]{Term}"})

        self.assertEqual(sample_to_dict(sample)["spans"][0]["label"], "Term")
        self.assertNotIn("gold_annotation", sample_to_dict(sample))

    def test_jsonl_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "samples.jsonl"
            original = [
                BootstrapSample(
                    id="s1",
                    text="abc",
                    spans=(BootstrapSpan(start=0, end=1, text="a", label="X"),),
                    metadata={"split": "dev"},
                )
            ]
            write_samples_jsonl(path, original)
            loaded = read_samples_jsonl(path)

        self.assertEqual(loaded, original)


class TestBootstrapCandidates(unittest.TestCase):
    def test_candidate_from_markup(self):
        candidate = candidate_from_dict(
            {
                "sample_id": "s1",
                "run_id": "run-1",
                "text": "heart failure",
                "annotation_markup": "[heart failure]{Term}",
                "model_confidence": 0.75,
            }
        )

        self.assertEqual(candidate.candidate_id, "run-1")
        self.assertEqual(candidate.model_confidence, 0.75)
        self.assertEqual(candidate.spans[0].label, "Term")

    def test_candidate_rejects_invalid_confidence(self):
        with self.assertRaises(BootstrapDataError):
            candidate_from_dict({"sample_id": "s1", "model_confidence": 1.5})


if __name__ == "__main__":
    unittest.main()
