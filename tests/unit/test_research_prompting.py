import unittest

from app.research.config import parse_research_config
from app.research.contracts import ResearchSample
from app.research.prompting import build_prompt
from app.research.retrieval import select_examples


class TestResearchPrompting(unittest.TestCase):
    def test_build_prompt_includes_constraints_and_examples(self):
        config = parse_research_config(
            {
                "name": "demo",
                "platform": "deepseek",
                "model": "deepseek-chat",
                "api_key_env": "DEEPSEEK_API_KEY",
                "definition": "Projection definition",
                "negative_constraints": ["Do not label every that-clause as projection."],
                "canonical_examples": [
                    {
                        "id": "ex-1",
                        "text": "She said hello.",
                        "annotation": "[said]{projection} hello.",
                        "explanation": "speech process",
                    }
                ],
                "hard_examples": [
                    {
                        "id": "ex-2",
                        "text": "The report, however, changed the review.",
                        "annotation": "[report]{projection}, however, changed the review.",
                        "explanation": "hard case",
                        "example_type": "hard",
                    }
                ],
            }
        )
        sample = ResearchSample(id="s1", text="She said the project was delayed.")
        examples = select_examples(config, sample)
        prompt = build_prompt(config, sample, examples)

        self.assertIn("任务名称：demo", prompt)
        self.assertIn("负向约束", prompt)
        self.assertIn("She said the project was delayed.", prompt)
        self.assertIn("ex-1", prompt)


if __name__ == "__main__":
    unittest.main()
