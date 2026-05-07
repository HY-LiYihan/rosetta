from pathlib import Path
import unittest

from app.services.annotation_service import (
    ANNOTATION_ASSISTANT_SYSTEM_PROMPTS,
    RUNTIME_PROMPT_SECTION_LABELS,
    RUNTIME_PROMPT_SECTION_ORDER,
    SUPPORTED_PROMPT_LANGUAGES,
)


class TestPromptCompositionDocs(unittest.TestCase):
    def test_prompt_composition_doc_tracks_runtime_prompt_contract(self):
        root = Path(__file__).resolve().parents[2]
        content = (root / "docs" / "user" / "PROMPT_COMPOSITION.md").read_text(encoding="utf-8")

        for language in SUPPORTED_PROMPT_LANGUAGES:
            with self.subTest(language=language):
                self.assertIn(ANNOTATION_ASSISTANT_SYSTEM_PROMPTS[language], content)
                labels = RUNTIME_PROMPT_SECTION_LABELS[language]
                for section_key in RUNTIME_PROMPT_SECTION_ORDER:
                    self.assertIn(labels[section_key], content)

        self.assertIn("ConceptPromptSpec", content)
        self.assertIn("输出格式", content)


if __name__ == "__main__":
    unittest.main()
