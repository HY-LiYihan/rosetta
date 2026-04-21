import unittest

from app.research.config import ResearchConfigError, parse_research_config


class TestResearchConfig(unittest.TestCase):
    def test_parse_research_config_accepts_valid_payload(self):
        payload = {
            "name": "demo",
            "platform": "deepseek",
            "model": "deepseek-chat",
            "api_key_env": "DEEPSEEK_API_KEY",
            "definition": "demo definition",
            "canonical_examples": [
                {
                    "id": "ex-1",
                    "text": "She said hello.",
                    "annotation": "[said]{projection} hello.",
                    "explanation": "speech process",
                }
            ],
        }
        config = parse_research_config(payload)
        self.assertEqual(config.name, "demo")
        self.assertEqual(config.top_k_examples, 3)
        self.assertEqual(config.canonical_examples[0].example_type, "canonical")

    def test_parse_research_config_rejects_missing_examples(self):
        payload = {
            "name": "demo",
            "platform": "deepseek",
            "model": "deepseek-chat",
            "api_key_env": "DEEPSEEK_API_KEY",
            "definition": "demo definition",
        }
        with self.assertRaises(ResearchConfigError):
            parse_research_config(payload)


if __name__ == "__main__":
    unittest.main()
