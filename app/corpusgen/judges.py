from __future__ import annotations

from difflib import SequenceMatcher

from app.corpusgen.contracts import CorpusSpec, GenerationTask


def judge_generated_items(
    spec: CorpusSpec,
    task: GenerationTask,
    context_pack: dict,
    items: list[dict],
    accepted_items: list[dict],
) -> list[dict]:
    judged: list[dict] = []
    for item in items:
        issues: list[dict] = []
        prompt_text, response_text = _split_text_fields(spec, item)

        if not prompt_text:
            issues.append({"code": "missing_prompt", "message": "缺少问题或指令字段"})
        elif len(prompt_text) < spec.quality.min_prompt_chars:
            issues.append({"code": "short_prompt", "message": "问题或指令长度不足"})

        if not response_text:
            issues.append({"code": "missing_response", "message": "缺少回答或响应字段"})
        elif len(response_text) < spec.quality.min_response_chars:
            issues.append({"code": "short_response", "message": "回答或响应长度不足"})

        if str(item.get("language", "")).strip() != spec.language:
            issues.append({"code": "language_mismatch", "message": "语言字段与 spec 不一致"})
        if str(item.get("domain", "")).strip() != spec.domain:
            issues.append({"code": "domain_mismatch", "message": "领域字段与 spec 不一致"})

        source_ids = item.get("source_chunk_ids", [])
        if not isinstance(source_ids, list) or not source_ids:
            issues.append({"code": "missing_lineage", "message": "缺少有效的 source_chunk_ids"})
        else:
            allowed_ids = set(context_pack["source_chunk_ids"])
            if any(source_id not in allowed_ids for source_id in source_ids):
                issues.append({"code": "invalid_source", "message": "source_chunk_ids 包含未召回的 chunk"})

        body = f"{prompt_text}\n{response_text}"
        for banned in spec.banned_terms:
            if banned and banned in body:
                issues.append({"code": "banned_term", "message": f"命中禁用词：{banned}"})
                break

        if spec.quality.require_term_overlap:
            term_pack = context_pack.get("term_pack", [])
            if term_pack and not any(term in body for term in term_pack):
                issues.append({"code": "weak_grounding", "message": "内容没有显式覆盖召回术语"})

        similarity = _max_similarity(spec, item, accepted_items)
        if similarity >= spec.quality.max_similarity:
            issues.append({"code": "duplicate", "message": f"与已有样本相似度过高: {similarity:.2f}"})

        status = "accepted" if not issues else "review"
        judged.append(
            {
                "status": status,
                "issues": issues,
                "item": item,
                "task_id": task.task_id,
            }
        )
    return judged


def _split_text_fields(spec: CorpusSpec, item: dict) -> tuple[str, str]:
    if spec.target_schema == "qa":
        return str(item.get("question", "")).strip(), str(item.get("answer", "")).strip()
    return str(item.get("instruction", "")).strip(), str(item.get("response", "")).strip()


def _max_similarity(spec: CorpusSpec, item: dict, accepted_items: list[dict]) -> float:
    prompt_text, response_text = _split_text_fields(spec, item)
    current = f"{prompt_text}\n{response_text}"
    if not current.strip():
        return 0.0

    best = 0.0
    for existing in accepted_items:
        other_prompt, other_response = _split_text_fields(spec, existing)
        other = f"{other_prompt}\n{other_response}"
        best = max(best, SequenceMatcher(None, current, other).ratio())
    return best
