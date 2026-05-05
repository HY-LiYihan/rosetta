from __future__ import annotations

import json
from typing import Any

from app.core.models import AnnotationSpan, AnnotationTask
from app.domain.annotation_doc import legacy_string_to_spans

OFFICIAL_SAMPLE_KEY = "professional_ner"
OFFICIAL_PROJECT_ID = "project-official-professional-ner"
OFFICIAL_GUIDELINE_ID = "guideline-official-professional-ner"
OFFICIAL_GOLD_SET_ID = "gold-official-professional-ner"
OFFICIAL_CONCEPT_VERSION_ID = "concept-version-official-professional-ner-v1"
OFFICIAL_GOLD_TASK_PREFIX = "official-gold"
OFFICIAL_LABEL = "Term"


PROFESSIONAL_NER_EXAMPLE: dict[str, Any] = {
    "project_name": "专业命名实体标注",
    "project_description": "用于从英文科学与技术科普文本中抽取可命名、可边界化的专业实体，包括研究对象、方法、材料、设备、过程和领域专门概念。",
    "concept_name": "专业命名实体",
    "brief": "标出英文科学与技术文本中具有明确领域含义、可命名且边界清楚的专业实体。",
    "labels": OFFICIAL_LABEL,
    "boundary_rules": "\n".join(
        [
            "优先标注最小完整实体名称。",
            "包含形成实体名称所必需的修饰成分，但不要扩展到整句或普通描述。",
            "多词实体应整体标注，不拆成单个普通词。",
            "同一句中出现多个相互独立的专业实体时，应分别标注。",
        ]
    ),
    "negative_rules": "\n".join(
        [
            "不标注过泛、无明确领域实体含义的普通词。",
            "不标注没有专业概念指向的修辞表达。",
            "不标注机构名、新闻来源名或人物名，除非任务明确要求。",
            "不标注只表达程度、时间、数量或情态的普通短语。",
        ]
    ),
    "output_format": "[原文]{标签}",
    "gold_examples": [
        {
            "text": "Quantum dots can emit precise colors when excited by light.",
            "annotation": "[Quantum dots]{Term} can emit precise colors when excited by light.",
        },
        {
            "text": "The telescope detected faint gravitational waves from a distant merger.",
            "annotation": "The telescope detected faint [gravitational waves]{Term} from a distant merger.",
        },
        {
            "text": "Researchers used CRISPR gene editing to repair a mutation in the cells.",
            "annotation": "Researchers used [CRISPR gene editing]{Term} to repair a mutation in the cells.",
        },
        {
            "text": "Perovskite solar cells may improve the efficiency of next-generation panels.",
            "annotation": "[Perovskite solar cells]{Term} may improve the efficiency of next-generation panels.",
        },
        {
            "text": "The experiment measured superconductivity at extremely low temperatures.",
            "annotation": "The experiment measured [superconductivity]{Term} at extremely low temperatures.",
        },
        {
            "text": "A new catalyst accelerated hydrogen production during electrolysis.",
            "annotation": "A new [catalyst]{Term} accelerated [hydrogen production]{Term} during [electrolysis]{Term}.",
        },
        {
            "text": "The spacecraft mapped methane plumes in the planet's atmosphere.",
            "annotation": "The spacecraft mapped [methane plumes]{Term} in the planet's [atmosphere]{Term}.",
        },
        {
            "text": "The vaccine candidate uses messenger RNA to train immune cells.",
            "annotation": "The vaccine candidate uses [messenger RNA]{Term} to train [immune cells]{Term}.",
        },
        {
            "text": "Scientists observed protein folding with high-resolution microscopy.",
            "annotation": "Scientists observed [protein folding]{Term} with [high-resolution microscopy]{Term}.",
        },
        {
            "text": "The battery prototype uses a solid-state electrolyte.",
            "annotation": "The battery prototype uses a [solid-state electrolyte]{Term}.",
        },
        {
            "text": "Neutrino oscillation reveals that neutrinos have mass.",
            "annotation": "[Neutrino oscillation]{Term} reveals that [neutrinos]{Term} have mass.",
        },
        {
            "text": "The reactor design improves plasma confinement in fusion experiments.",
            "annotation": "The reactor design improves [plasma confinement]{Term} in [fusion experiments]{Term}.",
        },
        {
            "text": "Carbon capture systems remove carbon dioxide from industrial exhaust.",
            "annotation": "[Carbon capture systems]{Term} remove [carbon dioxide]{Term} from industrial exhaust.",
        },
        {
            "text": "The sensor detects biomarkers associated with early-stage disease.",
            "annotation": "The sensor detects [biomarkers]{Term} associated with early-stage disease.",
        },
        {
            "text": "Nanoporous membranes can filter salts from seawater.",
            "annotation": "[Nanoporous membranes]{Term} can filter salts from seawater.",
        },
    ],
}


def professional_ner_gold_jsonl() -> str:
    return "\n".join(
        json.dumps(row, ensure_ascii=False) for row in PROFESSIONAL_NER_EXAMPLE["gold_examples"]
    )


def professional_ner_description() -> str:
    return "\n".join(
        [
            f"概念描述：{PROFESSIONAL_NER_EXAMPLE['brief']}",
            "边界规则：",
            *[f"- {line}" for line in PROFESSIONAL_NER_EXAMPLE["boundary_rules"].splitlines()],
        ]
    )


def professional_ner_gold_tasks(prefix: str = OFFICIAL_GOLD_TASK_PREFIX) -> list[AnnotationTask]:
    tasks: list[AnnotationTask] = []
    for index, row in enumerate(PROFESSIONAL_NER_EXAMPLE["gold_examples"], start=1):
        spans = []
        for span in legacy_string_to_spans(row["text"], row["annotation"]):
            spans.append(
                AnnotationSpan(
                    id=str(span.get("id", f"T{len(spans) + 1}")),
                    start=int(span.get("start", -1)),
                    end=int(span.get("end", -1)),
                    text=str(span.get("text", "")),
                    label=str(span.get("label") or OFFICIAL_LABEL),
                    implicit=bool(span.get("implicit", False)),
                )
            )
        task = AnnotationTask(
            id=f"{prefix}-{index:05d}",
            text=str(row["text"]),
            spans=tuple(spans),
            answer="accept",
            meta={
                "source": "official_sample_gold",
                "official_sample": True,
                "sample_key": OFFICIAL_SAMPLE_KEY,
                "example_index": index,
                "runtime_annotation": str(row["annotation"]),
            },
        )
        task.validate()
        tasks.append(task)
    return tasks
