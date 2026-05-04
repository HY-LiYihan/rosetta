import json
import unittest

from app.ui.examples import PROFESSIONAL_NER_EXAMPLE, professional_ner_gold_jsonl
from app.ui.i18n import REQUIRED_UI_KEYS, TEXT, get_text
from app.workflows.bootstrap import gold_task_from_markup


class TestUiI18nExamples(unittest.TestCase):
    def test_required_i18n_keys_exist_for_supported_languages(self):
        for language, mapping in TEXT.items():
            with self.subTest(language=language):
                missing = [key for key in REQUIRED_UI_KEYS if key not in mapping or not mapping[key]]
                self.assertEqual(missing, [])

    def test_i18n_formatting(self):
        self.assertEqual(get_text("zh-CN", "batch_run.parsed", count=15), "已解析出 15 条标注任务。")
        self.assertEqual(get_text("en-US", "batch_run.parsed", count=15), "Parsed 15 annotation tasks.")

    def test_professional_ner_example_gold_jsonl_is_valid(self):
        rows = [json.loads(line) for line in professional_ner_gold_jsonl().splitlines()]
        self.assertEqual(len(rows), 15)
        self.assertEqual(PROFESSIONAL_NER_EXAMPLE["labels"], "Term")
        self.assertEqual(PROFESSIONAL_NER_EXAMPLE["project_name"], "专业命名实体标注")
        tasks = [
            gold_task_from_markup(f"gold-{index:05d}", row["text"], row["annotation"], "Term")
            for index, row in enumerate(rows, start=1)
        ]
        self.assertEqual(len(tasks), 15)
        self.assertTrue(all(task.spans for task in tasks))


if __name__ == "__main__":
    unittest.main()
