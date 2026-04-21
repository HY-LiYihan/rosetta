from __future__ import annotations

from app.infrastructure.debug import log_debug_event
from app.services.corpus_studio_service import (
    CorpusStudioError,
    build_article_generation_prompt,
    build_intent_payload,
    build_judge_prompt,
    build_strategy_prompt,
    build_title_expansion_prompt,
    chunk_list,
    normalize_articles_payload,
    normalize_judge_payload,
    normalize_strategy_plan,
    normalize_title_expansion,
    parse_json_payload,
)
from app.services.platform_service import get_chat_response


def generate_corpus_plan(
    brief: str,
    language: str,
    genre: str,
    domain: str,
    audience: str,
    tone: str,
    total_articles: int,
    target_words: int,
    hard_constraints: str,
    extra_notes: str,
    available_config: dict,
    selected_platform: str | None,
    selected_model: str | None,
    temperature: float,
    current_plan: dict | None = None,
    feedback: str = "",
) -> dict:
    try:
        api_key = _resolve_api_key(available_config, selected_platform)
        intent = build_intent_payload(
            brief=brief,
            language=language,
            genre=genre,
            domain=domain,
            audience=audience,
            tone=tone,
            total_articles=total_articles,
            target_words=target_words,
            hard_constraints=hard_constraints,
            extra_notes=extra_notes,
        )
        prompt = build_strategy_prompt(intent, current_plan=current_plan, feedback=feedback)
        log_debug_event("corpus_studio_plan_requested", {"intent": intent, "feedback": feedback})
        raw_response = get_chat_response(
            platform=selected_platform,
            api_key=api_key,
            model=selected_model,
            messages=[
                {"role": "system", "content": "你是一个严谨的语料策划助手，只能输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        payload = parse_json_payload(raw_response)
        plan = normalize_strategy_plan(payload, intent)
        log_debug_event("corpus_studio_plan_received", {"plan": plan})
        return {
            "ok": True,
            "plan": plan,
            "raw_response": raw_response,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def generate_sample_articles(
    plan: dict,
    selected_titles: list[str],
    target_words: int,
    available_config: dict,
    selected_platform: str | None,
    selected_model: str | None,
    temperature: float,
    feedback: str = "",
) -> dict:
    try:
        api_key = _resolve_api_key(available_config, selected_platform)
        titles = [title for title in selected_titles if title.strip()][:2]
        if not titles:
            raise CorpusStudioError("至少需要选择一个样稿标题")
        prompt = build_article_generation_prompt(plan, titles, target_words=target_words, stage="sample", feedback=feedback)
        raw_response = get_chat_response(
            platform=selected_platform,
            api_key=api_key,
            model=selected_model,
            messages=[
                {"role": "system", "content": "你是一个专业写作助手，只能输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        payload = parse_json_payload(raw_response)
        articles = normalize_articles_payload(payload, plan=plan, titles=titles, stage="sample")
        if not articles:
            raise CorpusStudioError("模型没有返回可用的样稿")
        return {
            "ok": True,
            "articles": articles,
            "raw_response": raw_response,
            "titles": titles,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def generate_corpus_collection(
    plan: dict,
    selected_titles: list[str],
    total_articles: int,
    target_words: int,
    batch_size: int,
    available_config: dict,
    selected_platform: str | None,
    selected_model: str | None,
    temperature: float,
    feedback: str = "",
) -> dict:
    try:
        api_key = _resolve_api_key(available_config, selected_platform)
        title_pool = [title.strip() for title in selected_titles if title.strip()]
        if not title_pool:
            raise CorpusStudioError("至少需要一个确认后的标题")

        if len(title_pool) < total_articles:
            title_pool = _expand_titles(
                plan=plan,
                existing_titles=title_pool,
                desired_count=total_articles,
                feedback=feedback,
                api_key=api_key,
                selected_platform=selected_platform,
                selected_model=selected_model,
                temperature=max(temperature, 0.5),
            )

        target_titles = title_pool[:total_articles]
        articles: list[dict] = []
        batch_runs: list[dict] = []
        for batch_titles in chunk_list(target_titles, batch_size):
            prompt = build_article_generation_prompt(plan, batch_titles, target_words=target_words, stage="batch", feedback=feedback)
            raw_response = get_chat_response(
                platform=selected_platform,
                api_key=api_key,
                model=selected_model,
                messages=[
                    {"role": "system", "content": "你是一个专业写作助手，只能输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            payload = parse_json_payload(raw_response)
            batch_articles = normalize_articles_payload(payload, plan=plan, titles=batch_titles, stage="batch")
            if len(batch_articles) < len(batch_titles):
                missing_titles = batch_titles[len(batch_articles):]
                for missing_title in missing_titles:
                    single_prompt = build_article_generation_prompt(
                        plan,
                        [missing_title],
                        target_words=target_words,
                        stage="batch",
                        feedback=feedback,
                    )
                    single_raw_response = get_chat_response(
                        platform=selected_platform,
                        api_key=api_key,
                        model=selected_model,
                        messages=[
                            {"role": "system", "content": "你是一个专业写作助手，只能输出 JSON。"},
                            {"role": "user", "content": single_prompt},
                        ],
                        temperature=temperature,
                    )
                    single_payload = parse_json_payload(single_raw_response)
                    batch_articles.extend(
                        normalize_articles_payload(single_payload, plan=plan, titles=[missing_title], stage="batch")
                    )

            articles.extend(batch_articles)
            batch_runs.append(
                {
                    "titles": batch_titles,
                    "raw_response": raw_response,
                    "article_count": len(batch_articles),
                }
            )

        return {
            "ok": True,
            "titles": target_titles,
            "articles": articles[:total_articles],
            "batch_runs": batch_runs,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def judge_corpus_collection(
    plan: dict,
    articles: list[dict],
    available_config: dict,
    selected_platform: str | None,
    selected_model: str | None,
    temperature: float,
) -> dict:
    try:
        api_key = _resolve_api_key(available_config, selected_platform)
        judge_chunks = chunk_list([article["title"] for article in articles], 5)
        chunk_results: list[dict] = []
        title_to_article = {article["title"]: article for article in articles}
        for title_batch in judge_chunks:
            article_batch = [title_to_article[title] for title in title_batch]
            prompt = build_judge_prompt(plan, article_batch)
            raw_response = get_chat_response(
                platform=selected_platform,
                api_key=api_key,
                model=selected_model,
                messages=[
                    {"role": "system", "content": "你是一个严格的质量评审助手，只能输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            payload = parse_json_payload(raw_response)
            chunk_results.append(
                {
                    "raw_response": raw_response,
                    "judgement": normalize_judge_payload(payload, article_batch),
                }
            )

        merged_items: list[dict] = []
        summaries: list[str] = []
        global_issues: list[str] = []
        for result in chunk_results:
            merged_items.extend(result["judgement"]["items"])
            if result["judgement"]["summary"]:
                summaries.append(result["judgement"]["summary"])
            global_issues.extend(result["judgement"]["global_issues"])

        averages = {
            metric: round(
                sum(item["scores"][metric] for item in merged_items) / len(merged_items),
                2,
            )
            for metric in ["brief_alignment", "style_fit", "clarity", "scientific_tone", "usefulness"]
        } if merged_items else {}

        return {
            "ok": True,
            "summary": " ".join(summaries).strip(),
            "global_issues": _dedupe(global_issues),
            "items": merged_items,
            "averages": averages,
            "chunk_results": chunk_results,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _expand_titles(
    plan: dict,
    existing_titles: list[str],
    desired_count: int,
    feedback: str,
    api_key: str,
    selected_platform: str,
    selected_model: str,
    temperature: float,
) -> list[str]:
    prompt = build_title_expansion_prompt(plan, existing_titles, desired_count, feedback=feedback)
    raw_response = get_chat_response(
        platform=selected_platform,
        api_key=api_key,
        model=selected_model,
        messages=[
            {"role": "system", "content": "你是一个选题编辑，只能输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    payload = parse_json_payload(raw_response)
    return normalize_title_expansion(payload, existing_titles, desired_count)


def _resolve_api_key(available_config: dict, selected_platform: str | None) -> str:
    if not selected_platform:
        raise CorpusStudioError("没有可用的 AI 平台，请检查 secrets.toml 配置")
    platform_config = available_config.get(selected_platform, {})
    api_key = platform_config.get("api_key")
    if not api_key:
        raise CorpusStudioError(f"平台 {selected_platform} 缺少 API Key")
    return api_key


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for item in items:
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            results.append(normalized)
    return results
