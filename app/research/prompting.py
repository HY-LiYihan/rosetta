from __future__ import annotations

import json

from app.research.contracts import ResearchConfig, ResearchExample, ResearchSample


def _format_rules(title: str, rules: tuple[str, ...]) -> str:
    if not rules:
        return f"{title}：无\n"
    lines = [f"{title}："]
    lines.extend(f"{index}. {rule}" for index, rule in enumerate(rules, start=1))
    return "\n".join(lines) + "\n"


def _format_examples(examples: list[ResearchExample]) -> str:
    if not examples:
        return "上下文示例：无\n"

    chunks: list[str] = ["上下文示例："]
    for index, example in enumerate(examples, start=1):
        label = "典型示例" if example.example_type == "canonical" else "易错示例"
        chunks.append(f"示例 {index}（{label}, id={example.id}）:")
        chunks.append(
            json.dumps(
                {
                    "text": example.text,
                    "annotation": example.annotation,
                    "explanation": example.explanation,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if example.rationale:
            chunks.append(f"审查说明: {example.rationale}")
    return "\n".join(chunks) + "\n"


def build_prompt(config: ResearchConfig, sample: ResearchSample, examples: list[ResearchExample]) -> str:
    sections = [
        "你正在执行科研标注任务。请先严格根据定义判断，再返回结构化 JSON。",
        f"任务名称：{config.name}",
    ]
    if config.description:
        sections.append(f"任务说明：{config.description}")

    sections.extend(
        [
            f"操作化定义：{config.definition}",
            _format_rules("纳入标准", config.inclusion_rules).rstrip(),
            _format_rules("排除标准", config.exclusion_rules).rstrip(),
            _format_rules("负向约束", config.negative_constraints).rstrip(),
            _format_examples(examples).rstrip(),
            (
                "输出要求：仅返回 JSON，对象必须包含字段 "
                + ", ".join(config.output_contract)
                + "。annotation 必须使用 [原文]{标签} / [!隐含义]{标签} 格式。"
            ),
            f"待标注样本（id={sample.id}）：",
            sample.text,
        ]
    )
    return "\n\n".join(section for section in sections if section.strip())
