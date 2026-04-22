from __future__ import annotations

import json

from app.corpusgen.contracts import CorpusSpec, GenerationTask
from app.corpusgen.utils import strip_markdown_fences


def build_generation_prompt(
    spec: CorpusSpec,
    task: GenerationTask,
    context_pack: dict,
) -> str:
    if spec.target_schema == "qa":
        schema_hint = (
            '{"items":[{"question":"...","answer":"...","rationale":"...","source_chunk_ids":["..."]}]}'
        )
        field_hint = "每个 item 必须包含 question/answer/rationale/source_chunk_ids。"
    else:
        schema_hint = (
            '{"items":[{"instruction":"...","response":"...","rationale":"...","source_chunk_ids":["..."]}]}'
        )
        field_hint = "每个 item 必须包含 instruction/response/rationale/source_chunk_ids。"

    return f"""请基于下列压缩上下文，生成 {task.target_count} 条高质量科研语料。

任务要求：
- 领域：{spec.domain}
- 语言：{spec.language}
- 体裁：{task.genre_name}
- 聚焦主题：{task.focus}
- 风格：{task.style}
- 难度：{task.difficulty}
- 额外约束：{task.instruction}

压缩上下文：
{context_pack["compressed_context"]}

输出要求：
- 只输出 JSON，不要包含 Markdown 代码块或解释。
- {field_hint}
- `source_chunk_ids` 必须从这个集合中选择：{context_pack["source_chunk_ids"]}。
- 内容必须可追溯到给定证据，不能凭空添加人名、实验结果、年份或出处。
- 问题或指令应当多样化，不要只改写同一句话。

JSON 模板：
{schema_hint}
"""


def parse_generation_response(raw_response: str) -> tuple[list[dict], str | None]:
    cleaned = strip_markdown_fences(raw_response)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return [], f"无法解析 JSON: {exc}"

    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("items")
    else:
        items = None

    if not isinstance(items, list):
        return [], "响应缺少 `items` 列表"

    normalized: list[dict] = []
    for item in items:
        if isinstance(item, dict):
            normalized.append(item)
    if not normalized:
        return [], "响应中没有可用 item"
    return normalized, None


def normalize_generated_items(
    spec: CorpusSpec,
    task: GenerationTask,
    context_pack: dict,
    items: list[dict],
) -> list[dict]:
    normalized: list[dict] = []
    allowed_ids = set(context_pack["source_chunk_ids"])
    for index, item in enumerate(items, start=1):
        source_chunk_ids = item.get("source_chunk_ids", context_pack["source_chunk_ids"])
        if isinstance(source_chunk_ids, str):
            source_chunk_ids = [source_chunk_ids]
        if not isinstance(source_chunk_ids, list):
            source_chunk_ids = list(context_pack["source_chunk_ids"])
        filtered_ids = [str(chunk_id) for chunk_id in source_chunk_ids if str(chunk_id) in allowed_ids]
        if not filtered_ids:
            filtered_ids = list(context_pack["source_chunk_ids"])

        base = {
            "id": f"{task.task_id}-item-{index:03d}",
            "schema": spec.target_schema,
            "language": item.get("language", spec.language),
            "domain": item.get("domain", spec.domain),
            "genre": task.genre_name,
            "focus": task.focus,
            "rationale": str(item.get("rationale", "")).strip(),
            "source_chunk_ids": filtered_ids,
            "lineage": {
                "spec_name": spec.name,
                "task_id": task.task_id,
                "compression_mode": "brief+evidence+terms+failures",
                "retrieved_chunk_ids": list(context_pack["source_chunk_ids"]),
            },
        }
        if spec.target_schema == "qa":
            base["question"] = str(item.get("question", "")).strip()
            base["answer"] = str(item.get("answer", "")).strip()
        else:
            base["instruction"] = str(item.get("instruction", "")).strip()
            base["response"] = str(item.get("response", "")).strip()
        normalized.append(base)
    return normalized
