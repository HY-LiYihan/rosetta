import unittest

from app.workflows.bootstrap import (
    build_llm_adamw_trace,
    estimate_text_gradients,
    finalize_candidate_trace,
    length_penalized_loss,
    segment_prompt,
)


def _validation_result():
    return {
        "passed": ["gold-01"],
        "failed": ["gold-02"],
        "unstable": ["gold-03"],
        "details": [
            {
                "task_id": "gold-02",
                "route": "failed",
                "missing_spans": [{"text": "quantum dots", "label": "Term"}],
                "extra_spans": [],
                "score": 0.0,
            },
            {
                "task_id": "gold-03",
                "route": "unstable",
                "missing_spans": [],
                "extra_spans": [{"text": "researchers", "label": "Term"}],
                "score": 0.5,
            },
        ],
    }


class TestPromptOptimizer(unittest.TestCase):
    def test_segment_prompt_marks_schema_and_format_as_fixed(self):
        description = "\n".join(
            [
                "概念描述：标出科学术语。",
                "标签集合：Term",
                "边界规则：标最小完整术语。",
                "排除规则：不标泛化词。",
                "输出格式：[原文]{标签}",
            ]
        )

        segments = segment_prompt(description)

        self.assertEqual([segment.kind for segment in segments], [
            "task_definition",
            "label_schema",
            "boundary_rules",
            "negative_rules",
            "output_format",
        ])
        fixed = {segment.kind for segment in segments if not segment.mutable}
        self.assertEqual(fixed, {"label_schema", "output_format"})

    def test_estimate_text_gradients_prioritizes_boundary_rules(self):
        description = "\n".join(
            [
                "概念描述：标出科学术语。",
                "边界规则：标最小完整术语。",
                "排除规则：不标泛化词。",
            ]
        )

        gradients = estimate_text_gradients(
            description,
            _validation_result(),
            "gold-02 漏标 quantum dots",
            {"loss": 16.5},
        )

        self.assertTrue(gradients)
        self.assertEqual(gradients[0].segment_id, "seg-02-boundary_rules")
        self.assertEqual(gradients[0].method, "mask_ablation")
        self.assertIn(gradients[0].direction, {"stabilize_boundary", "expand_recall_boundary", "tighten_boundary"})

    def test_build_trace_records_gradient_and_segments(self):
        trace = build_llm_adamw_trace(
            "概念描述：标出科学术语。\n边界规则：标最小完整术语。",
            _validation_result(),
            "失败摘要仅用于日志",
            {"loss": 16.5},
        )

        self.assertEqual(trace["optimizer"], "llm_adamw")
        self.assertTrue(trace["segments"])
        self.assertTrue(trace["text_gradients"])
        self.assertEqual(trace["proposed_trace"]["current_loss"], 16.5)

    def test_length_penalized_loss_penalizes_only_growth(self):
        longer = length_penalized_loss({"loss": 1.0}, "short", "short plus more text")
        shorter = length_penalized_loss({"loss": 1.0}, "short plus more text", "short")

        self.assertGreater(longer["loss"], longer["raw_loss"])
        self.assertEqual(shorter["loss"], shorter["raw_loss"])
        self.assertGreater(longer["length_delta"], 0)
        self.assertLess(shorter["length_delta"], 0)

    def test_finalize_candidate_trace_records_loss_delta_and_acceptance(self):
        base_trace = build_llm_adamw_trace(
            "概念描述：标出科学术语。\n边界规则：标最小完整术语。",
            _validation_result(),
            "失败摘要仅用于日志",
            {"loss": 10.0},
        )

        trace = finalize_candidate_trace(
            base_trace,
            "candidate-01",
            "概念描述：标出科学术语。",
            "概念描述：标出科学术语。\n边界规则：包含多词术语。",
            {"loss": 10.0},
            {"loss": 6.0},
            True,
        )

        self.assertEqual(trace["candidate_id"], "candidate-01")
        self.assertTrue(trace["trace"]["accepted"])
        self.assertEqual(trace["trace"]["loss_delta"], 4.0)
        self.assertGreater(trace["trace"]["length_delta"], 0)


if __name__ == "__main__":
    unittest.main()
