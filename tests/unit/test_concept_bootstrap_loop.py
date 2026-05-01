import json
import tempfile
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

    def test_writes_failure_versions_until_max_rounds(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)

        def bad_predictor(system_prompt, messages, temperature):
            text = messages[-1]["content"].split("文本：", 1)[-1].strip()
            return json.dumps({"text": text, "annotation": "[Wrong]{Term}", "explanation": "wrong"})

        result = run_concept_refinement_loop(store, guideline_id, predictor=bad_predictor, max_rounds=2)

        self.assertFalse(result["stable"])
        self.assertEqual(len(result["rounds"]), 2)
        self.assertEqual(result["rounds"][0]["pass_count"], 0)
        versions = store.list_concept_versions(guideline_id=guideline_id, limit=10)
        generated = [row for row in versions if row["payload"].get("metadata", {}).get("revision_source") == "concept_refinement_loop"]
        self.assertEqual(len(generated), 2)
        self.assertTrue(generated[0]["payload"]["metadata"]["failure_summary"])

    def test_llm_revision_saves_only_clean_description(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)

        def predictor(system_prompt, messages, temperature):
            prompt = messages[-1]["content"]
            if "优化下面的概念阐释" in prompt:
                return "\n".join(
                    [
                        "概念描述：标出英文科普新闻中的硬科学专业术语。",
                        "标签集合：Term",
                        "边界规则：多词术语保持完整边界，只标注原文中明确出现的专业概念。",
                        "排除规则：不纳入普通泛化词、人物名、机构名和新闻来源。",
                        "输出格式：[原文]{标签}",
                    ]
                )
            text = prompt.split("文本：", 1)[-1].strip()
            return json.dumps({"text": text, "annotation": "[Wrong]{Term}", "explanation": "wrong"})

        run_concept_refinement_loop(store, guideline_id, predictor=predictor, max_rounds=1)

        versions = store.list_concept_versions(guideline_id=guideline_id, limit=10)
        generated = [row for row in versions if row["payload"].get("metadata", {}).get("revision_source") == "concept_refinement_loop"]
        description = generated[0]["payload"]["description"]
        metadata = generated[0]["payload"]["metadata"]
        self.assertIn("概念描述：标出英文科普新闻中的硬科学专业术语。", description)
        self.assertNotIn("gold-", description)
        self.assertNotIn("失败摘要", description)
        self.assertTrue(metadata["failure_summary"])
        self.assertTrue(metadata["failure_cases"])
        self.assertIn("概念描述：标出英文科普新闻中的硬科学专业术语。", metadata["raw_revision_response"])

    def test_dirty_llm_revision_falls_back_to_clean_prompt(self):
        tmp, store, guideline_id = _store_with_guideline(gold_count=15)
        self.addCleanup(tmp.cleanup)

        def predictor(system_prompt, messages, temperature):
            prompt = messages[-1]["content"]
            if "优化下面的概念阐释" in prompt:
                return "概念描述：bad\n失败摘要：gold-00001 漏标 Quantum dots\n修订建议：复制日志"
            text = prompt.split("文本：", 1)[-1].strip()
            return json.dumps({"text": text, "annotation": "[Wrong]{Term}", "explanation": "wrong"})

        run_concept_refinement_loop(store, guideline_id, predictor=predictor, max_rounds=1)

        versions = store.list_concept_versions(guideline_id=guideline_id, limit=10)
        generated = [row for row in versions if row["payload"].get("metadata", {}).get("revision_source") == "concept_refinement_loop"]
        payload = generated[0]["payload"]
        self.assertNotIn("gold-00001", payload["description"])
        self.assertNotIn("失败摘要", payload["description"])
        self.assertNotIn("漏标", payload["description"])
        self.assertIn("fallback_to_previous_description", payload["metadata"]["sanitizer_warnings"])

    def test_default_deepseek_model_is_v4_pro(self):
        self.assertEqual(PLATFORM_CONFIGS["deepseek"].default_model, "deepseek-v4-pro")


if __name__ == "__main__":
    unittest.main()
