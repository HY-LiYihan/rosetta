import unittest

from app.services.annotation_service import ANNOTATION_ASSISTANT_SYSTEM_PROMPT
from app.workflows.annotation import run_agentic_annotation


class TestWorkflowAnnotation(unittest.TestCase):
    def test_run_agentic_annotation(self):
        seen = {}

        def predictor(system_prompt, messages, temperature):
            seen["system_prompt"] = system_prompt
            return '{"text":"abc","annotation":"[abc]{Term}","explanation":"ok"}'

        result = run_agentic_annotation(
            concept={"name": "Term", "prompt": "Mark terms", "examples": []},
            input_text="abc",
            predictor=predictor,
            platform="mock",
            model="mock-model",
            temperature=0.1,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["agent_result"].run.workflow, "annotation")
        self.assertIn("history_entry", result)
        self.assertEqual(seen["system_prompt"], ANNOTATION_ASSISTANT_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
