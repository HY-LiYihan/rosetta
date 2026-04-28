from __future__ import annotations

import json

HARD_SCIENCE_TERM_EXAMPLE = {
    "project_name": "硬科学科普术语标注",
    "project_description": "用于从英文硬科学科普新闻中抽取科学概念、技术名词、实验对象和物理过程术语。",
    "concept_name": "硬科学术语",
    "brief": "标出英文科普新闻中与物理、化学、天文、生物医学、材料科学或工程技术直接相关的专业术语。",
    "labels": "Term",
    "boundary_rules": "\n".join(
        [
            "优先标注最小完整术语。",
            "包含必要修饰词，例如 quantum dots、gravitational waves。",
            "不要把整句话、普通动词或泛泛描述标成术语。",
            "多词术语应整体标注，不拆成单个普通词。",
        ]
    ),
    "negative_rules": "\n".join(
        [
            "不标注 science、researchers、study 这类过泛词。",
            "不标注没有明确科学概念含义的修辞表达。",
            "不标注机构名、新闻来源名或人物名，除非任务明确要求。",
            "不标注只表达程度或时间的普通短语。",
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


def hard_science_gold_jsonl() -> str:
    return "\n".join(
        json.dumps(row, ensure_ascii=False) for row in HARD_SCIENCE_TERM_EXAMPLE["gold_examples"]
    )
