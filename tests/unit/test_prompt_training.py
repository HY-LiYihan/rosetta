import json
import tempfile
import unittest
from pathlib import Path

from app.core.models import Project
from app.runtime.store import RuntimeStore
from app.workflows.bootstrap import (
    LLM_OPTIMIZE_ONLY,
    LLM_REFLECTION,
    TEXT_GRADIENT_ADAMW,
    PromptTrainingConfig,
    build_llm_optimize_only_prompt,
    build_training_feedback_prompt,
    gold_task_from_markup,
    run_prompt_training_experiment,
    save_guideline_package,
)


def _store_with_guideline(gold_count: int = 15):
    tmp = tempfile.TemporaryDirectory()
    store = RuntimeStore(Path(tmp.name) / "rosetta.sqlite3")
    store.upsert_project(Project(id="p1", name="Project"))
    gold_tasks = [
        gold_task_from_markup(
            task_id=f"gold-{index:05d}",
            text=f"Quantum term {index} appears here.",
            annotation_markup=f"[Quantum term {index}]{{Term}} appears here.",
            label_hint="Term",
        )
        for index in range(1, gold_count + 1)
    ]
    package = save_guideline_package(
        store,
        project_id="p1",
        name="Term",
        brief="Mark scientific terms.",
        labels=["Term"],
        boundary_rules=["Use the minimal complete term."],
        negative_rules=["Do not mark generic words."],
        gold_tasks=gold_tasks,
    )
    return tmp, store, package["guideline"].id


def _wrong_annotation(prompt: str) -> str:
    text = prompt.split("文本：", 1)[-1].strip()
    return json.dumps({"text": text, "annotation": "[Wrong]{Term}", "explanation": "wrong"})


def _correct_annotation(prompt: str) -> str:
    text = prompt.split("文本：", 1)[-1].strip()
    term = text.split(" appears here.", 1)[0]
    return json.dumps({"text": text, "annotation": f"[{term}]{{Term}} appears here.", "explanation": "matched"})


class TestPromptTraining(unittest.TestCase):
    def test_llm_optimize_only_prompt_has_no_failure_or_gradient_details(self):
        prompt = build_llm_optimize_only_prompt("概念描述：标出科学术语。\n标签集合：Term")

        forbidden = ["失败摘要", "gold-", "漏标", "多标", "loss", "文本梯度"]
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, prompt)

    def test_training_selects_method_that_reaches_all_gold_examples(self):
        tmp, store, guideline_id = _store_with_guideline()
        self.addCleanup(tmp.cleanup)

        def predictor(system_prompt, messages, temperature):
            prompt = messages[-1]["content"]
            if system_prompt == "你是概念阐释改写助手。只返回最终可用的概念阐释正文。":
                return "\n".join(
                    [
                        "概念描述：标出科学文本中带编号或专名结构的明确领域术语。",
                        "标签集合：Term",
                        "边界规则：由大写专名词和类型词组成、后接编号时，应整体标注最小完整术语。",
                        "排除规则：不标普通泛化词。",
                        "输出格式：[原文]{标签}",
                    ]
                )
            if system_prompt in {
                "你是概念提示词优化助手。只返回最终可用的概念阐释正文。",
                "你是概念阐释反思优化助手。只返回最终可用的概念阐释正文。",
            }:
                return "\n".join(
                    [
                        "概念描述：仍然只笼统说明科学术语。",
                        "标签集合：Term",
                        "边界规则：边界不确定时不标。",
                        "排除规则：不标普通词。",
                        "输出格式：[原文]{标签}",
                    ]
                )
            if "带编号或专名结构" in prompt:
                return _correct_annotation(prompt)
            return _wrong_annotation(prompt)

        result = run_prompt_training_experiment(
            store,
            guideline_id,
            predictor=predictor,
            config=PromptTrainingConfig(candidate_count=1, max_rounds=3),
        )

        self.assertEqual(result["status"], "stable")
        self.assertEqual(result["best_method"], TEXT_GRADIENT_ADAMW)
        self.assertEqual(result["best_pass_count"], 15)
        self.assertIn("带编号或专名结构", result["best_description"])
        self.assertTrue(result["leakage_report"]["final_prompt_clean"])
        winning_method = next(row for row in result["method_results"] if row["method"] == TEXT_GRADIENT_ADAMW)
        self.assertGreater(winning_method["llm_call_count"], 0)
        self.assertGreater(winning_method["estimated_tokens"], 0)
        self.assertGreaterEqual(winning_method["elapsed_seconds"], 0.0)
        self.assertIn("estimated_tokens", result["rounds"][0])
        versions = store.list_concept_versions(guideline_id=guideline_id, limit=10)
        training_versions = [row["payload"] for row in versions if row["payload"].get("metadata", {}).get("prompt_training")]
        self.assertEqual(training_versions[0]["metadata"]["best_method"], TEXT_GRADIENT_ADAMW)
        self.assertTrue(training_versions[0]["metadata"]["reached_target"])
        self.assertTrue(training_versions[0]["metadata"]["leakage_summary"]["final_prompt_clean"])

    def test_all_methods_fail_without_marking_stable(self):
        tmp, store, guideline_id = _store_with_guideline()
        self.addCleanup(tmp.cleanup)

        def predictor(system_prompt, messages, temperature):
            if system_prompt != "你是严谨的标注校验助手，只输出 JSON。":
                return "\n".join(
                    [
                        "概念描述：只保留一个模糊定义。",
                        "标签集合：Term",
                        "边界规则：不确定时不标。",
                        "排除规则：不标普通词。",
                        "输出格式：[原文]{标签}",
                    ]
                )
            return _wrong_annotation(messages[-1]["content"])

        result = run_prompt_training_experiment(
            store,
            guideline_id,
            predictor=predictor,
            config=PromptTrainingConfig(max_rounds=2, candidate_count=1),
            auto_apply=True,
        )

        self.assertEqual(result["status"], "needs_revision")
        self.assertLess(result["best_pass_count"], 15)
        versions = store.list_concept_versions(guideline_id=guideline_id, limit=10)
        training_version = next(row["payload"] for row in versions if row["payload"].get("metadata", {}).get("prompt_training"))
        self.assertFalse(training_version["metadata"]["reached_target"])
        self.assertFalse(training_version["metadata"]["auto_applied"])
        self.assertNotEqual(training_version["metadata"].get("status"), "stable")

    def test_reflection_sanitizes_diagnostics_from_final_description(self):
        tmp, store, guideline_id = _store_with_guideline()
        self.addCleanup(tmp.cleanup)

        def predictor(system_prompt, messages, temperature):
            prompt = messages[-1]["content"]
            if system_prompt == "你是概念阐释反思优化助手。只返回最终可用的概念阐释正文。":
                return "\n".join(
                    [
                        "以下是优化后的概念阐释：",
                        "概念描述：标出科学文本中带编号或专名结构的明确领域术语。",
                        "标签集合：Term",
                        "边界规则：由大写专名词和类型词组成、后接编号时，应整体标注最小完整术语。",
                        "失败摘要：gold-00001 漏标 Quantum term 1",
                        "排除规则：不标普通泛化词。",
                        "输出格式：[原文]{标签}",
                    ]
                )
            if "带编号或专名结构" in prompt:
                return _correct_annotation(prompt)
            return _wrong_annotation(prompt)

        result = run_prompt_training_experiment(
            store,
            guideline_id,
            predictor=predictor,
            config=PromptTrainingConfig(methods=(LLM_REFLECTION,), max_rounds=2, candidate_count=1),
        )

        self.assertEqual(result["status"], "stable")
        self.assertEqual(result["best_method"], LLM_REFLECTION)
        self.assertNotIn("gold-00001", result["best_description"])
        self.assertNotIn("Quantum term", result["best_description"])
        self.assertNotIn("失败摘要", result["best_description"])
        self.assertNotIn("漏标", result["best_description"])
        versions = store.list_concept_versions(guideline_id=guideline_id, limit=10)
        training_version = next(row["payload"] for row in versions if row["payload"].get("metadata", {}).get("prompt_training"))
        self.assertEqual(training_version["metadata"]["best_method"], LLM_REFLECTION)
        self.assertTrue(training_version["metadata"]["method_comparison"])

    def test_reflection_feedback_prompt_is_marked_training_feedback_only(self):
        result = {
            "details": [
                {
                    "task_id": "gold-00001",
                    "route": "failed",
                    "text": "Quantum term 1 appears here.",
                    "gold_spans": [{"text": "Quantum term 1", "label": "Term"}],
                    "predicted_spans": [{"text": "Wrong", "label": "Term"}],
                    "missing_spans": [{"text": "Quantum term 1", "label": "Term"}],
                    "extra_spans": [{"text": "Wrong", "label": "Term"}],
                }
            ]
        }

        prompt = build_training_feedback_prompt("概念描述：标出科学术语。", result, "gold-00001 漏标 Quantum term 1")

        self.assertIn("training_feedback_only=true", prompt)
        self.assertIn("Quantum term 1", prompt)

    def test_candidate_copying_gold_answer_is_blocked(self):
        tmp, store, guideline_id = _store_with_guideline()
        self.addCleanup(tmp.cleanup)

        def predictor(system_prompt, messages, temperature):
            if system_prompt == "你是概念阐释反思优化助手。只返回最终可用的概念阐释正文。":
                return "\n".join(
                    [
                        "概念描述：标出 Quantum term 这类明确术语。",
                        "标签集合：Term",
                        "边界规则：Quantum term 加数字编号时整体标注。",
                        "排除规则：不标普通泛化词。",
                        "输出格式：[原文]{标签}",
                    ]
                )
            if "Quantum term 这类" in messages[-1]["content"]:
                return _correct_annotation(messages[-1]["content"])
            return _wrong_annotation(messages[-1]["content"])

        result = run_prompt_training_experiment(
            store,
            guideline_id,
            predictor=predictor,
            config=PromptTrainingConfig(methods=(LLM_REFLECTION,), max_rounds=1, candidate_count=1),
        )

        self.assertEqual(result["status"], "needs_revision")
        self.assertGreater(result["leakage_report"]["candidate_blocked_count"], 0)
        blocked = result["rounds"][0]["candidate_evaluations"][0]
        self.assertEqual(blocked["status"], "memorization_guard_blocked")
        self.assertFalse(blocked["memorization_passed"])

    def test_requires_target_gold_count(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=3)
        self.addCleanup(tmp.cleanup)

        with self.assertRaisesRegex(ValueError, "提示词优化训练需要 15 条金样例"):
            run_prompt_training_experiment(
                store,
                guideline_id,
                config=PromptTrainingConfig(methods=(LLM_OPTIMIZE_ONLY,)),
            )


if __name__ == "__main__":
    unittest.main()
