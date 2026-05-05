import json
import threading
import tempfile
import time
import unittest
from pathlib import Path

from app.core.models import Project
from app.infrastructure.llm.providers import PLATFORM_CONFIGS
from app.runtime.store import RuntimeStore
from app.workflows.bootstrap import (
    gold_task_from_markup,
    run_concept_refinement_loop,
    sanitize_concept_description,
    save_guideline_package,
    validate_gold_examples,
)


def _store_with_guideline(gold_count: int = 15):
    tmp = tempfile.TemporaryDirectory()
    store = RuntimeStore(Path(tmp.name) / "rosetta.sqlite3")
    store.upsert_project(Project(id="p1", name="Project"))
    gold_tasks = [
        gold_task_from_markup(
            task_id=f"gold-{index:02d}",
            text=f"Quantum term {index} appears here.",
            annotation_markup=f"[Quantum term {index}]{{Term}} appears here.",
            label_hint="Term",
        )
        for index in range(gold_count)
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


def _target_text_from_prompt(prompt: str) -> str:
    value = prompt.split("待标注文本：", 1)[-1].strip()
    return value.split("\n\n任务强调：", 1)[0].strip()


class TestConceptBootstrapLoop(unittest.TestCase):
    def test_sanitize_removes_failure_diagnostics_from_description(self):
        dirty = """以下是优化后的概念阐释：
概念描述：标出硬科学术语。
失败摘要：
gold-00001: 漏标 Quantum dots
修订建议：扩大失败样例范围。
标签集合：Term"""

        cleaned, warnings = sanitize_concept_description(dirty, fallback="概念描述：fallback")

        self.assertIn("概念描述：标出硬科学术语。", cleaned)
        self.assertIn("标签集合：Term", cleaned)
        self.assertNotIn("gold-00001", cleaned)
        self.assertNotIn("失败摘要", cleaned)
        self.assertNotIn("漏标", cleaned)
        self.assertTrue(warnings)

    def test_requires_target_gold_count(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=3)
        self.addCleanup(tmp.cleanup)

        with self.assertRaisesRegex(ValueError, "15 条金样例"):
            run_concept_refinement_loop(store, guideline_id)

    def test_stops_when_all_gold_examples_pass(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)

        result = run_concept_refinement_loop(store, guideline_id, max_rounds=5)

        self.assertTrue(result["stable"])
        self.assertEqual(len(result["rounds"]), 1)
        self.assertEqual(result["rounds"][0]["pass_count"], 15)
        guideline = store.get_guideline(guideline_id)["payload"]
        self.assertEqual(guideline["status"], "stable")

    def test_validation_uses_concurrency_and_reports_progress(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)
        state = {"active": 0, "max_active": 0}
        lock = threading.Lock()
        events: list[dict] = []

        def predictor(system_prompt, messages, temperature):
            with lock:
                state["active"] += 1
                state["max_active"] = max(state["max_active"], state["active"])
            try:
                time.sleep(0.01)
                prompt = messages[-1]["content"]
                self.assertIn("请根据以下概念定义标注文本。", prompt)
                self.assertIn("概念定义：", prompt)
                self.assertIn("标注格式：", prompt)
                self.assertIn("通用格式示例（只说明输出格式，不代表当前任务概念）：", prompt)
                self.assertIn("待标注文本：", prompt)
                self.assertIn("任务强调：", prompt)
                self.assertNotIn("不要参考金答案", prompt)
                text = _target_text_from_prompt(prompt)
                term = text.split(" appears here.", 1)[0]
                return json.dumps({"text": text, "annotation": f"[{term}]{{Term}} appears here.", "explanation": "matched"})
            finally:
                with lock:
                    state["active"] -= 1

        result = validate_gold_examples(
            store,
            guideline_id,
            predictor=predictor,
            concurrency=4,
            progress_callback=events.append,
        )

        self.assertEqual(result["status"], "stable")
        self.assertEqual(result["concurrency"], 4)
        self.assertEqual(len(result["details"]), 15)
        self.assertGreater(state["max_active"], 1)
        self.assertEqual(len(events), 15)
        self.assertEqual(events[-1]["completed"], 15)

    def test_extra_spans_are_not_counted_as_passed(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)

        def extra_predictor(system_prompt, messages, temperature):
            text = _target_text_from_prompt(messages[-1]["content"])
            term = text.split(" appears here.", 1)[0]
            return json.dumps({"text": text, "annotation": f"[{term}]{{Term}} appears [here]{{Term}}.", "explanation": "extra"})

        result = run_concept_refinement_loop(store, guideline_id, predictor=extra_predictor, max_rounds=1)

        self.assertFalse(result["stable"])
        self.assertEqual(result["rounds"][0]["pass_count"], 0)
        self.assertGreater(result["rounds"][0]["loss"], 0.0)

    def test_stops_without_improving_candidate_and_records_loss(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)

        def bad_predictor(system_prompt, messages, temperature):
            text = _target_text_from_prompt(messages[-1]["content"])
            return json.dumps({"text": text, "annotation": "[Wrong]{Term}", "explanation": "wrong"})

        result = run_concept_refinement_loop(store, guideline_id, predictor=bad_predictor, max_rounds=2)

        self.assertFalse(result["stable"])
        self.assertEqual(len(result["rounds"]), 1)
        self.assertEqual(result["rounds"][0]["status"], "no_improvement")
        self.assertEqual(result["rounds"][0]["pass_count"], 0)
        versions = store.list_concept_versions(guideline_id=guideline_id, limit=10)
        generated = [row for row in versions if row["payload"].get("metadata", {}).get("revision_source") == "concept_refinement_loop"]
        self.assertEqual(len(generated), 1)
        self.assertTrue(generated[0]["payload"]["metadata"]["failure_summary"])
        self.assertEqual(generated[0]["payload"]["metadata"]["accepted_candidate_id"], "current")
        self.assertGreater(generated[0]["payload"]["metadata"]["current_loss"]["loss"], 0.0)

    def test_loss_search_selects_candidate_that_improves_gold_score(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)

        def predictor(system_prompt, messages, temperature):
            prompt = messages[-1]["content"]
            if "优化下面的概念阐释" in prompt:
                if "提高召回" in prompt:
                    return "\n".join(
                        [
                            "概念描述：标出英文科普新闻中的硬科学专业术语，必须包含 Quantum term 这类明确科学术语。",
                            "标签集合：Term",
                            "边界规则：保留最小完整术语，Quantum term 加数字编号时整体标注。",
                            "排除规则：不标普通泛化词。",
                            "输出格式：[原文]{标签}",
                        ]
                    )
                return "\n".join(
                    [
                        "概念描述：只标非常保守的科学术语。",
                        "标签集合：Term",
                        "边界规则：边界不确定时不标。",
                        "排除规则：不标普通词。",
                        "输出格式：[原文]{标签}",
                    ]
                )
            text = _target_text_from_prompt(prompt)
            if "Quantum term 这类" not in prompt:
                return json.dumps({"text": text, "annotation": "[Wrong]{Term}", "explanation": "wrong"})
            term = text.split(" appears here.", 1)[0]
            return json.dumps({"text": text, "annotation": f"[{term}]{{Term}} appears here.", "explanation": "matched"})

        result = run_concept_refinement_loop(store, guideline_id, predictor=predictor, max_rounds=3, candidate_count=3)

        self.assertTrue(result["stable"])
        self.assertEqual(len(result["rounds"]), 1)
        self.assertEqual(result["rounds"][0]["status"], "stable")
        self.assertNotEqual(result["rounds"][0]["accepted_candidate_id"], "current")
        self.assertGreater(result["rounds"][0]["loss_delta"], 0.0)
        self.assertIn("Quantum term 这类", result["final_description"])
        versions = store.list_concept_versions(guideline_id=guideline_id, limit=10)
        generated = [row for row in versions if row["payload"].get("metadata", {}).get("revision_source") == "concept_refinement_loop"]
        metadata = generated[0]["payload"]["metadata"]
        self.assertEqual(metadata["optimizer"], "loss_search")
        self.assertEqual(metadata["prompt_optimizer"], "llm_adamw")
        self.assertEqual(metadata["selected_loss"]["raw_loss"], 0.0)
        self.assertGreaterEqual(metadata["selected_loss"]["loss"], 0.0)
        self.assertEqual(metadata["prompt_optimization_trace"]["optimizer"], "llm_adamw")
        self.assertTrue(metadata["prompt_optimization_trace"]["trace"]["accepted"])
        self.assertGreater(metadata["prompt_optimization_trace"]["trace"]["loss_delta"], 0.0)
        self.assertTrue(metadata["candidate_evaluations"])

    def test_llm_revision_saves_only_clean_description(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)

        def predictor(system_prompt, messages, temperature):
            prompt = messages[-1]["content"]
            if "优化下面的概念阐释" in prompt:
                return "\n".join(
                    [
                        "概念描述：标出英文科普新闻中的硬科学专业术语，必须包含 Quantum term 这类明确科学术语。",
                        "标签集合：Term",
                        "边界规则：多词术语保持完整边界，只标注原文中明确出现的专业概念；Quantum term 加数字编号时整体标注。",
                        "排除规则：不纳入普通泛化词、人物名、机构名和新闻来源。",
                        "输出格式：[原文]{标签}",
                    ]
                )
            text = _target_text_from_prompt(prompt)
            if "Quantum term 这类" not in prompt:
                return json.dumps({"text": text, "annotation": "[Wrong]{Term}", "explanation": "wrong"})
            term = text.split(" appears here.", 1)[0]
            return json.dumps({"text": text, "annotation": f"[{term}]{{Term}} appears here.", "explanation": "matched"})

        run_concept_refinement_loop(store, guideline_id, predictor=predictor, max_rounds=1)

        versions = store.list_concept_versions(guideline_id=guideline_id, limit=10)
        generated = [row for row in versions if row["payload"].get("metadata", {}).get("revision_source") == "concept_refinement_loop"]
        description = generated[0]["payload"]["description"]
        metadata = generated[0]["payload"]["metadata"]
        self.assertIn("概念描述：标出英文科普新闻中的硬科学专业术语", description)
        self.assertNotIn("gold-", description)
        self.assertNotIn("失败摘要", description)
        self.assertTrue(metadata["failure_summary"])
        self.assertTrue(metadata["failure_cases"])
        self.assertIn("概念描述：标出英文科普新闻中的硬科学专业术语", metadata["raw_revision_response"])
        self.assertNotEqual(metadata["accepted_candidate_id"], "current")
        self.assertEqual(metadata["prompt_optimizer"], "llm_adamw")
        self.assertIn("prompt_optimization_trace", metadata)
        self.assertTrue(
            any(
                candidate.get("prompt_optimization_trace", {}).get("trace", {}).get("accepted")
                for candidate in metadata["candidate_evaluations"]
            )
        )

    def test_dirty_llm_revision_falls_back_to_clean_prompt(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)

        def predictor(system_prompt, messages, temperature):
            prompt = messages[-1]["content"]
            if "优化下面的概念阐释" in prompt:
                return "概念描述：bad\n失败摘要：gold-00001 漏标 Quantum dots\n修订建议：复制日志"
            text = _target_text_from_prompt(prompt)
            return json.dumps({"text": text, "annotation": "[Wrong]{Term}", "explanation": "wrong"})

        run_concept_refinement_loop(store, guideline_id, predictor=predictor, max_rounds=1)

        versions = store.list_concept_versions(guideline_id=guideline_id, limit=10)
        generated = [row for row in versions if row["payload"].get("metadata", {}).get("revision_source") == "concept_refinement_loop"]
        payload = generated[0]["payload"]
        self.assertNotIn("gold-00001", payload["description"])
        self.assertNotIn("失败摘要", payload["description"])
        self.assertNotIn("漏标", payload["description"])
        candidate_warnings = [
            warning
            for candidate in payload["metadata"]["candidate_evaluations"]
            for warning in candidate.get("sanitizer_warnings", [])
        ]
        self.assertIn("fallback_to_previous_description", candidate_warnings)
        self.assertEqual(payload["metadata"]["accepted_candidate_id"], "current")

    def test_default_deepseek_model_is_v4_pro(self):
        self.assertEqual(PLATFORM_CONFIGS["deepseek"].default_model, "deepseek-v4-pro")


if __name__ == "__main__":
    unittest.main()
