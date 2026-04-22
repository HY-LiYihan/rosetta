from __future__ import annotations

import json
import math
from datetime import datetime

from app.corpusgen.utils import dedupe_strings, strip_markdown_fences


class CorpusStudioError(ValueError):
    """Raised when corpus studio payloads are invalid or incomplete."""


def build_intent_payload(
    brief: str,
    language: str,
    genre: str,
    domain: str,
    audience: str,
    tone: str,
    total_articles: int,
    target_words: int,
    hard_constraints: str = "",
    extra_notes: str = "",
) -> dict:
    normalized_brief = brief.strip()
    if not normalized_brief:
        raise CorpusStudioError("一句话 brief 不能为空")

    return {
        "brief": normalized_brief,
        "language": language.strip() or "zh",
        "genre": genre.strip() or "general article",
        "domain": domain.strip() or "general",
        "audience": audience.strip() or "general audience",
        "tone": tone.strip() or "clear and informative",
        "total_articles": max(1, int(total_articles)),
        "target_words": max(120, int(target_words)),
        "hard_constraints": hard_constraints.strip(),
        "extra_notes": extra_notes.strip(),
    }


def build_strategy_prompt(intent: dict, current_plan: dict | None = None, feedback: str = "") -> str:
    current_plan_block = (
        json.dumps(current_plan, ensure_ascii=False, indent=2)
        if current_plan
        else "无"
    )
    feedback_block = feedback.strip() or "无"
    return f"""你是一个资深语料策划编辑。你的任务是把用户的一句话需求扩展成一个可以逐步确认的语料生成方案。

用户原始需求：
{json.dumps(intent, ensure_ascii=False, indent=2)}

当前策略草案（如有）：
{current_plan_block}

本轮微调反馈：
{feedback_block}

请完成以下工作：
1. 将 brief 精炼成更可执行的生成目标。
2. 给出一段策略摘要，说明这批语料要覆盖什么内容与风格。
3. 给出 6-10 个候选标题。
4. 任选其中 2 个标题，说明为什么适合作为样稿确认。
5. 给出生成规则、风格要求、judge 重点与潜在风险。

只输出 JSON，不要输出 Markdown。格式严格如下：
{{
  "refined_brief": "...",
  "strategy_summary": "...",
  "generation_rules": ["...", "..."],
  "title_candidates": ["...", "..."],
  "sample_angles": [
    {{
      "title": "...",
      "angle": "...",
      "why_it_works": "..."
    }}
  ],
  "style_profile": ["...", "..."],
  "judge_focus": ["...", "..."],
  "risk_notes": ["...", "..."]
}}
"""


def parse_json_payload(raw_response: str) -> dict:
    cleaned = strip_markdown_fences(raw_response)
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise CorpusStudioError("模型输出不是 JSON 对象")
    return payload


def normalize_strategy_plan(payload: dict, intent: dict) -> dict:
    refined_brief = str(payload.get("refined_brief", intent["brief"])).strip() or intent["brief"]
    strategy_summary = str(payload.get("strategy_summary", "")).strip() or refined_brief
    generation_rules = _clean_text_list(payload.get("generation_rules"), minimum=4)
    style_profile = _clean_text_list(payload.get("style_profile"), minimum=3)
    judge_focus = _clean_text_list(payload.get("judge_focus"), minimum=3)
    risk_notes = _clean_text_list(payload.get("risk_notes"), minimum=2)
    title_candidates = _clean_title_list(payload.get("title_candidates"), minimum=6)
    sample_angles = _normalize_sample_angles(payload.get("sample_angles"), title_candidates)

    return {
        "intent": intent,
        "refined_brief": refined_brief,
        "strategy_summary": strategy_summary,
        "generation_rules": generation_rules,
        "title_candidates": title_candidates,
        "sample_angles": sample_angles,
        "style_profile": style_profile,
        "judge_focus": judge_focus,
        "risk_notes": risk_notes,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def apply_plan_overrides(
    plan: dict,
    refined_brief: str,
    strategy_summary: str,
    generation_rules_text: str,
    title_candidates_text: str,
    style_profile_text: str,
    judge_focus_text: str,
    risk_notes_text: str,
) -> dict:
    updated = dict(plan)
    updated["refined_brief"] = refined_brief.strip() or plan["refined_brief"]
    updated["strategy_summary"] = strategy_summary.strip() or plan["strategy_summary"]
    updated["generation_rules"] = _text_block_to_list(generation_rules_text, minimum=2) or list(plan["generation_rules"])
    updated["title_candidates"] = _text_block_to_list(title_candidates_text, minimum=2) or list(plan["title_candidates"])
    updated["style_profile"] = _text_block_to_list(style_profile_text, minimum=2) or list(plan["style_profile"])
    updated["judge_focus"] = _text_block_to_list(judge_focus_text, minimum=2) or list(plan["judge_focus"])
    updated["risk_notes"] = _text_block_to_list(risk_notes_text, minimum=1) or list(plan["risk_notes"])
    updated["sample_angles"] = _normalize_sample_angles(plan.get("sample_angles"), updated["title_candidates"])
    updated["updated_at"] = datetime.now().isoformat(timespec="seconds")
    return updated


def build_article_generation_prompt(
    plan: dict,
    titles: list[str],
    target_words: int,
    stage: str,
    feedback: str = "",
) -> str:
    intent = plan["intent"]
    titles_payload = json.dumps(titles, ensure_ascii=False)
    feedback_block = feedback.strip() or "无"
    return f"""你是一个专业的语料写作助手。请根据给定方案为每个标题生成一篇完整文章。

当前阶段：{stage}
语料方案：
{json.dumps(plan, ensure_ascii=False, indent=2)}

本轮要生成的标题：
{titles_payload}

附加反馈：
{feedback_block}

写作要求：
1. 语言必须使用 {intent["language"]}。
2. 体裁是 {intent["genre"]}，领域是 {intent["domain"]}。
3. 目标受众：{intent["audience"]}。
4. 整体语气：{intent["tone"]}。
5. 每篇正文尽量接近 {target_words} 个词或同等信息量。
6. 内容要具体、自然，不要套模板，不要输出“作为 AI”之类的话。

只输出 JSON，不要输出 Markdown。格式严格如下：
{{
  "articles": [
    {{
      "title": "...",
      "summary": "...",
      "body": "...",
      "angle": "...",
      "keywords": ["...", "..."],
      "quality_notes": ["...", "..."]
    }}
  ]
}}
"""


def normalize_articles_payload(
    payload: dict,
    plan: dict,
    titles: list[str],
    stage: str,
) -> list[dict]:
    raw_articles = payload.get("articles", [])
    if not isinstance(raw_articles, list):
        raise CorpusStudioError("文章生成结果缺少 `articles` 列表")

    intent = plan["intent"]
    normalized: list[dict] = []
    for index, raw_article in enumerate(raw_articles, start=1):
        if not isinstance(raw_article, dict):
            continue
        title = str(raw_article.get("title", "")).strip()
        fallback_title = titles[index - 1] if index - 1 < len(titles) else f"Untitled-{index}"
        body = str(raw_article.get("body", "")).strip()
        summary = str(raw_article.get("summary", "")).strip()
        normalized.append(
            {
                "id": f"{stage}-article-{index:03d}",
                "title": title or fallback_title,
                "summary": summary,
                "body": body,
                "angle": str(raw_article.get("angle", "")).strip(),
                "keywords": _clean_text_list(raw_article.get("keywords"), minimum=0),
                "quality_notes": _clean_text_list(raw_article.get("quality_notes"), minimum=0),
                "language": intent["language"],
                "genre": intent["genre"],
                "domain": intent["domain"],
                "audience": intent["audience"],
                "tone": intent["tone"],
                "stage": stage,
                "word_count_estimate": estimate_length_units(body, intent["language"]),
            }
        )
    return normalized


def build_title_expansion_prompt(plan: dict, existing_titles: list[str], desired_count: int, feedback: str = "") -> str:
    return f"""你是一个选题编辑。请在保持同一语料方案的前提下补足标题池。

语料方案：
{json.dumps(plan, ensure_ascii=False, indent=2)}

已有标题：
{json.dumps(existing_titles, ensure_ascii=False)}

目标数量：{desired_count}
附加反馈：{feedback.strip() or "无"}

请补充新的、不重复的标题，使总数达到目标数量。
只输出 JSON：
{{
  "title_candidates": ["...", "..."]
}}
"""


def normalize_title_expansion(payload: dict, existing_titles: list[str], desired_count: int) -> list[str]:
    titles = _clean_title_list(payload.get("title_candidates"), minimum=0)
    seen = {title.strip() for title in existing_titles if title.strip()}
    results = list(existing_titles)
    for title in titles:
        if title not in seen:
            seen.add(title)
            results.append(title)
        if len(results) >= desired_count:
            break
    return results[:desired_count]


def build_judge_prompt(plan: dict, articles: list[dict]) -> str:
    compact_articles = [
        {
            "title": article["title"],
            "summary": article["summary"],
            "body": article["body"],
        }
        for article in articles
    ]
    return f"""你是一个严格的语料质量评审员。请根据给定方案评估每篇文章。

语料方案：
{json.dumps(plan, ensure_ascii=False, indent=2)}

待评估文章：
{json.dumps(compact_articles, ensure_ascii=False, indent=2)}

请针对每篇文章给出以下维度的 1-5 分评分：
- brief_alignment
- style_fit
- clarity
- scientific_tone
- usefulness

并给出：
- verdict: `pass` 或 `revise`
- issues: 最多 3 条
- revision_hint: 一句修改建议

只输出 JSON：
{{
  "summary": "...",
  "global_issues": ["...", "..."],
  "items": [
    {{
      "title": "...",
      "scores": {{
        "brief_alignment": 4,
        "style_fit": 4,
        "clarity": 4,
        "scientific_tone": 4,
        "usefulness": 4
      }},
      "verdict": "pass",
      "issues": ["..."],
      "revision_hint": "..."
    }}
  ]
}}
"""


def normalize_judge_payload(payload: dict, articles: list[dict]) -> dict:
    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        raise CorpusStudioError("judge 结果缺少 `items` 列表")

    article_by_title = {article["title"]: article for article in articles}
    normalized_items: list[dict] = []
    for index, raw_item in enumerate(raw_items, start=1):
        if not isinstance(raw_item, dict):
            continue
        title = str(raw_item.get("title", "")).strip()
        article = article_by_title.get(title)
        if article is None and index - 1 < len(articles):
            article = articles[index - 1]
            title = article["title"]

        scores = raw_item.get("scores", {})
        if not isinstance(scores, dict):
            scores = {}
        normalized_scores = {
            "brief_alignment": _normalize_score(scores.get("brief_alignment")),
            "style_fit": _normalize_score(scores.get("style_fit")),
            "clarity": _normalize_score(scores.get("clarity")),
            "scientific_tone": _normalize_score(scores.get("scientific_tone")),
            "usefulness": _normalize_score(scores.get("usefulness")),
        }
        normalized_items.append(
            {
                "title": title,
                "scores": normalized_scores,
                "verdict": "pass" if str(raw_item.get("verdict", "pass")).strip().lower() == "pass" else "revise",
                "issues": _clean_text_list(raw_item.get("issues"), minimum=0)[:3],
                "revision_hint": str(raw_item.get("revision_hint", "")).strip(),
                "article_id": article["id"] if article else None,
            }
        )

    averages = {
        metric: round(
            sum(item["scores"][metric] for item in normalized_items) / len(normalized_items),
            2,
        )
        for metric in ["brief_alignment", "style_fit", "clarity", "scientific_tone", "usefulness"]
    } if normalized_items else {}

    return {
        "summary": str(payload.get("summary", "")).strip(),
        "global_issues": _clean_text_list(payload.get("global_issues"), minimum=0),
        "items": normalized_items,
        "averages": averages,
    }


def build_corpus_studio_export_json(
    plan: dict | None,
    samples: dict | None,
    corpus: dict | None,
    judge: dict | None,
) -> str:
    payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "plan": plan,
        "samples": samples,
        "corpus": corpus,
        "judge": judge,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_corpus_studio_export_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"corpus_studio_{current.strftime('%Y%m%d_%H%M%S')}.json"


def estimate_length_units(text: str, language: str) -> int:
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return 0
    if language.lower().startswith("en"):
        return len(normalized.split())
    return len(normalized)


def _clean_text_list(value, minimum: int) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    else:
        items = []
    deduped = _dedupe(items)
    if minimum <= 0 or len(deduped) >= minimum:
        return deduped
    return deduped


def _clean_title_list(value, minimum: int) -> list[str]:
    titles = _clean_text_list(value, minimum=0)
    deduped = _dedupe(titles)
    if minimum > 0 and len(deduped) < minimum:
        deduped.extend(
            f"Title Candidate {index}"
            for index in range(1, minimum - len(deduped) + 1)
        )
    return deduped


def _normalize_sample_angles(value, fallback_titles: list[str]) -> list[dict]:
    normalized: list[dict] = []
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            angle = str(item.get("angle", "")).strip()
            why_it_works = str(item.get("why_it_works", "")).strip()
            if title and angle:
                normalized.append(
                    {
                        "title": title,
                        "angle": angle,
                        "why_it_works": why_it_works,
                    }
                )
    if normalized:
        return normalized[:2]
    return [
        {
            "title": title,
            "angle": "作为首轮样稿，用来确认选题方向、语气和信息密度。",
            "why_it_works": "这个标题能够快速暴露策略是否跑偏。",
        }
        for title in fallback_titles[:2]
    ]


def _normalize_score(value) -> float:
    try:
        score = float(value)
    except Exception:
        score = 3.0
    return min(5.0, max(1.0, round(score, 2)))


def _text_block_to_list(text: str, minimum: int) -> list[str]:
    items = [
        line.strip().lstrip("-").strip()
        for line in text.splitlines()
        if line.strip()
    ]
    deduped = dedupe_strings(items)
    if minimum > 0 and len(deduped) < minimum:
        return []
    return deduped


def _dedupe(items: list[str]) -> list[str]:
    return dedupe_strings(items)


def chunk_list(items: list[str], size: int) -> list[list[str]]:
    if size < 1:
        raise CorpusStudioError("chunk size 必须大于 0")
    return [items[start : start + size] for start in range(0, len(items), size)]


def recommended_batch_size(total_articles: int) -> int:
    return max(1, min(3, int(math.ceil(total_articles / 4))))
