import unittest

from app.services.corpus_studio_service import (
    apply_plan_overrides,
    build_judge_prompt,
    normalize_judge_payload,
    normalize_strategy_plan,
    parse_json_payload,
)


class TestCorpusStudioService(unittest.TestCase):
    def test_parse_json_payload_handles_code_fence(self):
        payload = parse_json_payload(
            """```json
{"refined_brief":"x"}
```"""
        )
        self.assertEqual(payload["refined_brief"], "x")

    def test_normalize_strategy_plan_preserves_intent_and_titles(self):
        intent = {
            "brief": "英文硬科学科普新闻",
            "language": "en",
            "genre": "science news",
            "domain": "hard science",
            "audience": "general readers",
            "tone": "clear",
            "total_articles": 10,
            "target_words": 700,
            "hard_constraints": "",
            "extra_notes": "",
        }
        payload = {
            "refined_brief": "Generate English hard-science explainers with a news frame.",
            "strategy_summary": "Balance discovery, method and implication.",
            "generation_rules": ["Use clear leads", "Avoid hype", "Explain terms", "Stay concrete"],
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
                    "angle": "Lead with the new map, then explain the astrophysics.",
                    "why_it_works": "Tests whether the tone feels like science journalism.",
                }
            ],
            "style_profile": ["Readable", "newsy", "scientifically grounded"],
            "judge_focus": ["brief alignment", "clarity", "scientific tone"],
            "risk_notes": ["Do not invent data", "Avoid clickbait"],
        }
        plan = normalize_strategy_plan(payload, intent)
        self.assertEqual(plan["intent"]["language"], "en")
        self.assertEqual(len(plan["title_candidates"]), 6)
        self.assertEqual(plan["sample_angles"][0]["title"], "Dark Matter Map Reveals Hidden Cosmic Bridges")

    def test_apply_plan_overrides_and_judge_payload(self):
        plan = {
            "intent": {"language": "en", "genre": "science news", "domain": "hard science", "audience": "general readers", "tone": "clear"},
            "refined_brief": "brief",
            "strategy_summary": "summary",
            "generation_rules": ["r1", "r2"],
            "title_candidates": ["t1", "t2"],
            "sample_angles": [{"title": "t1", "angle": "a", "why_it_works": "w"}],
            "style_profile": ["s1", "s2"],
            "judge_focus": ["j1", "j2"],
            "risk_notes": ["risk1"],
        }
        updated = apply_plan_overrides(plan, "brief2", "summary2", "r1\nr2\nr3", "t1\nt2\nt3", "s1\ns2", "j1\nj2", "risk1\nrisk2")
        self.assertEqual(updated["refined_brief"], "brief2")
        self.assertIn("t3", updated["title_candidates"])

        judge_payload = {
            "summary": "overall good",
            "global_issues": ["some titles too similar"],
            "items": [
                {
                    "title": "t1",
                    "scores": {
                        "brief_alignment": 4,
                        "style_fit": 5,
                        "clarity": 4,
                        "scientific_tone": 4,
                        "usefulness": 5,
                    },
                    "verdict": "pass",
                    "issues": ["minor repetition"],
                    "revision_hint": "tighten paragraph transitions",
                }
            ],
        }
        articles = [{"id": "a1", "title": "t1"}]
        judged = normalize_judge_payload(judge_payload, articles)
        self.assertEqual(judged["items"][0]["article_id"], "a1")
        self.assertEqual(judged["averages"]["usefulness"], 5.0)

    def test_build_judge_prompt_keeps_full_body(self):
        plan = {"refined_brief": "brief"}
        body = "word " * 500
        prompt = build_judge_prompt(
            plan,
            [{"title": "t1", "summary": "s1", "body": body}],
        )
        self.assertIn(body.strip(), prompt)


if __name__ == "__main__":
    unittest.main()
