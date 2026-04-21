import json
import unittest
from unittest.mock import patch

from app.services.corpus_studio_flow_service import (
    generate_corpus_collection,
    generate_corpus_plan,
    generate_sample_articles,
    judge_corpus_collection,
)


AVAILABLE_CONFIG = {
    "zhipuai": {
        "api_key": "test-key",
    }
}


class TestCorpusStudioFlowService(unittest.TestCase):
    @patch("app.services.corpus_studio_flow_service.get_chat_response")
    def test_generate_plan_and_samples(self, mock_chat):
        mock_chat.side_effect = [
            json.dumps(
                {
                    "refined_brief": "Generate English hard-science news articles.",
                    "strategy_summary": "Keep the corpus factual and readable.",
                    "generation_rules": ["Use concrete findings", "Avoid hype", "Explain terms", "Keep a news peg"],
                    "title_candidates": [
                        "Dark Matter Map Reveals Hidden Cosmic Bridges",
                        "Why New Battery Cathodes Last Longer Than Expected",
                        "Climate Models Get Sharper With Ocean Microdata",
                        "Lab-Grown Crystal Points to Safer Quantum Sensors",
                        "What a Mars Core Study Changes for Planet Formation",
                        "A New Telescope Filter Finds Faint Exoplanet Weather",
                    ],
                    "sample_angles": [
                        {
                            "title": "Dark Matter Map Reveals Hidden Cosmic Bridges",
                            "angle": "news lead + implications",
                            "why_it_works": "tests the tone",
                        }
                    ],
                    "style_profile": ["Readable", "newsy", "grounded"],
                    "judge_focus": ["brief alignment", "clarity", "scientific tone"],
                    "risk_notes": ["do not invent results", "avoid clickbait"],
                },
                ensure_ascii=False,
            ),
            json.dumps(
                {
                    "articles": [
                        {
                            "title": "Dark Matter Map Reveals Hidden Cosmic Bridges",
                            "summary": "Astronomers stitched together a sharper map of dark matter.",
                            "body": "Astronomers combined lensing observations and simulation constraints to build a sharper map of dark matter structures across several cosmic regions. The story explains what was measured, why it matters, and what remains uncertain.",
                            "angle": "lead with the new map",
                            "keywords": ["dark matter", "cosmology"],
                            "quality_notes": ["clear lead", "keeps uncertainty visible"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
        ]

        plan_result = generate_corpus_plan(
            brief="英文硬科学科普新闻",
            language="en",
            genre="science news",
            domain="hard science",
            audience="general readers",
            tone="clear",
            total_articles=12,
            target_words=700,
            hard_constraints="Avoid clickbait",
            extra_notes="Prefer astronomy and climate science",
            available_config=AVAILABLE_CONFIG,
            selected_platform="zhipuai",
            selected_model="glm-5",
            temperature=0.6,
        )
        self.assertTrue(plan_result["ok"])
        sample_result = generate_sample_articles(
            plan=plan_result["plan"],
            selected_titles=plan_result["plan"]["title_candidates"][:1],
            target_words=700,
            available_config=AVAILABLE_CONFIG,
            selected_platform="zhipuai",
            selected_model="glm-5",
            temperature=0.7,
        )
        self.assertTrue(sample_result["ok"])
        self.assertEqual(sample_result["articles"][0]["language"], "en")

    @patch("app.services.corpus_studio_flow_service.get_chat_response")
    def test_generate_sample_articles_repairs_invalid_json(self, mock_chat):
        plan = {
            "intent": {
                "brief": "英文硬科学科普新闻",
                "language": "en",
                "genre": "science news",
                "domain": "hard science",
                "audience": "general readers",
                "tone": "clear",
                "total_articles": 4,
                "target_words": 700,
                "hard_constraints": "",
                "extra_notes": "",
            },
            "refined_brief": "Generate English hard-science news articles.",
            "strategy_summary": "Keep the corpus factual and readable.",
            "generation_rules": ["Use concrete findings", "Avoid hype"],
            "title_candidates": ["Dark Matter Map Reveals Hidden Cosmic Bridges"],
            "sample_angles": [{"title": "Dark Matter Map Reveals Hidden Cosmic Bridges", "angle": "a", "why_it_works": "w"}],
            "style_profile": ["Readable", "newsy"],
            "judge_focus": ["brief alignment", "clarity", "scientific tone"],
            "risk_notes": ["do not invent results"],
        }
        mock_chat.side_effect = [
            '{"articles":[{"title":"Dark Matter Map Reveals Hidden Cosmic Bridges","summary":"Astronomers built a sharper dark matter map." "body":"broken json"}]}',
            json.dumps(
                {
                    "articles": [
                        {
                            "title": "Dark Matter Map Reveals Hidden Cosmic Bridges",
                            "summary": "Astronomers built a sharper dark matter map.",
                            "body": "Astronomers combined lensing observations and simulation constraints to map hidden structures in several cosmic regions while explaining what remains uncertain.",
                            "angle": "news lead",
                            "keywords": ["dark matter"],
                            "quality_notes": ["clear lead"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
        ]
        result = generate_sample_articles(
            plan=plan,
            selected_titles=["Dark Matter Map Reveals Hidden Cosmic Bridges"],
            target_words=700,
            available_config=AVAILABLE_CONFIG,
            selected_platform="zhipuai",
            selected_model="glm-5",
            temperature=0.7,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["articles"][0]["title"], "Dark Matter Map Reveals Hidden Cosmic Bridges")
        self.assertEqual(mock_chat.call_count, 2)

    @patch("app.services.corpus_studio_flow_service.get_chat_response")
    def test_generate_corpus_and_judge(self, mock_chat):
        plan = {
            "intent": {
                "brief": "英文硬科学科普新闻",
                "language": "en",
                "genre": "science news",
                "domain": "hard science",
                "audience": "general readers",
                "tone": "clear",
                "total_articles": 4,
                "target_words": 700,
                "hard_constraints": "",
                "extra_notes": "",
            },
            "refined_brief": "Generate English hard-science news articles.",
            "strategy_summary": "Keep the corpus factual and readable.",
            "generation_rules": ["Use concrete findings", "Avoid hype"],
            "title_candidates": [
                "Dark Matter Map Reveals Hidden Cosmic Bridges",
                "Why New Battery Cathodes Last Longer Than Expected",
            ],
            "sample_angles": [{"title": "Dark Matter Map Reveals Hidden Cosmic Bridges", "angle": "a", "why_it_works": "w"}],
            "style_profile": ["Readable", "newsy"],
            "judge_focus": ["brief alignment", "clarity", "scientific tone"],
            "risk_notes": ["do not invent results"],
        }

        mock_chat.side_effect = [
            json.dumps(
                {
                    "articles": [
                        {
                            "title": "Dark Matter Map Reveals Hidden Cosmic Bridges",
                            "summary": "Astronomers built a sharper dark matter map.",
                            "body": "Astronomers combined lensing observations and simulation constraints to map hidden structures across several cosmic regions. The article explains the method, the main result, and the remaining uncertainty in accessible language.",
                            "angle": "news lead",
                            "keywords": ["dark matter"],
                            "quality_notes": ["clear lead"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            json.dumps(
                {
                    "articles": [
                        {
                            "title": "Why New Battery Cathodes Last Longer Than Expected",
                            "summary": "Materials scientists found a stabilizing mechanism in cathodes.",
                            "body": "Materials scientists identified a stabilizing mechanism that slows structural decay in a family of battery cathodes. The article explains why the result matters, how the researchers tested it, and what practical limits remain.",
                            "angle": "materials science lead",
                            "keywords": ["battery", "materials science"],
                            "quality_notes": ["balanced conclusion"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            json.dumps(
                {
                    "summary": "Both articles fit the brief and maintain a credible science-news tone.",
                    "global_issues": ["The corpus would benefit from more topic diversity in a larger run."],
                    "items": [
                        {
                            "title": "Dark Matter Map Reveals Hidden Cosmic Bridges",
                            "scores": {
                                "brief_alignment": 5,
                                "style_fit": 4,
                                "clarity": 4,
                                "scientific_tone": 5,
                                "usefulness": 4,
                            },
                            "verdict": "pass",
                            "issues": [],
                            "revision_hint": "Could add one sentence about observational limits.",
                        },
                        {
                            "title": "Why New Battery Cathodes Last Longer Than Expected",
                            "scores": {
                                "brief_alignment": 4,
                                "style_fit": 4,
                                "clarity": 5,
                                "scientific_tone": 4,
                                "usefulness": 4,
                            },
                            "verdict": "pass",
                            "issues": [],
                            "revision_hint": "Tighten the ending slightly.",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
        ]

        corpus_result = generate_corpus_collection(
            plan=plan,
            selected_titles=plan["title_candidates"],
            total_articles=2,
            target_words=700,
            batch_size=1,
            available_config=AVAILABLE_CONFIG,
            selected_platform="zhipuai",
            selected_model="glm-5",
            temperature=0.7,
        )
        self.assertTrue(corpus_result["ok"])
        self.assertEqual(len(corpus_result["articles"]), 2)

        judge_result = judge_corpus_collection(
            plan=plan,
            articles=corpus_result["articles"],
            available_config=AVAILABLE_CONFIG,
            selected_platform="zhipuai",
            selected_model="glm-5",
            temperature=0.2,
        )
        self.assertTrue(judge_result["ok"])
        self.assertEqual(len(judge_result["items"]), 2)
        self.assertGreaterEqual(judge_result["averages"]["brief_alignment"], 4.0)


if __name__ == "__main__":
    unittest.main()
