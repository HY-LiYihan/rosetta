import unittest
from unittest.mock import patch

from app.services.annotation_flow_service import run_annotation


class TestAnnotationFlowService(unittest.TestCase):
    def test_run_annotation_no_platform(self):
        result = run_annotation(
            concept={"name": "A", "prompt": "p", "examples": []},
            input_text="text",
            available_config={},
            selected_platform=None,
            selected_model=None,
            temperature=0.3,
        )
        self.assertFalse(result["ok"])

    @patch("app.services.annotation_flow_service.get_chat_response")
    def test_run_annotation_success(self, mock_chat):
        mock_chat.return_value = '{"text":"t","annotation":"[t]{demo}","explanation":"e"}'
        result = run_annotation(
            concept={"name": "A", "prompt": "p", "examples": []},
            input_text="text",
            available_config={"deepseek": {"api_key": "sk", "name": "DeepSeek"}},
            selected_platform="deepseek",
            selected_model="deepseek-chat",
            temperature=0.3,
        )
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["parsed_result"])
        self.assertIn("history_entry", result)


if __name__ == "__main__":
    unittest.main()
