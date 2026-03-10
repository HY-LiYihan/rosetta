import unittest
from unittest.mock import patch

from app.services.platform_service import probe_available_platforms_from_secrets


class TestPlatformService(unittest.TestCase):
    @patch("app.services.platform_service.get_provider")
    @patch("app.services.platform_service.get_platform_configs")
    def test_probe_available_platforms_filters_invalid_provider(self, mock_configs, mock_get_provider):
        mock_configs.return_value = {
            "deepseek": {
                "name": "DeepSeek",
                "key_name": "deepseek_api_key",
                "default_model": "deepseek-chat",
            }
        }

        class DummyProvider:
            def list_models(self, api_key):
                return ["deepseek-chat", "deepseek-reasoner"]

        mock_get_provider.return_value = DummyProvider()

        available = probe_available_platforms_from_secrets({"deepseek_api_key": "k"})
        self.assertIn("deepseek", available)
        self.assertEqual(available["deepseek"]["default_model"], "deepseek-chat")

    @patch("app.services.platform_service.get_provider")
    @patch("app.services.platform_service.get_platform_configs")
    def test_probe_available_platforms_skips_missing_secrets(self, mock_configs, mock_get_provider):
        mock_configs.return_value = {
            "deepseek": {
                "name": "DeepSeek",
                "key_name": "deepseek_api_key",
                "default_model": "deepseek-chat",
            }
        }
        available = probe_available_platforms_from_secrets({})
        self.assertEqual(available, {})
        mock_get_provider.assert_not_called()


if __name__ == "__main__":
    unittest.main()
