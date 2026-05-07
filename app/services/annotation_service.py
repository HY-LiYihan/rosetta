import json
from datetime import datetime

from app.domain.annotation_doc import make_annotation_doc, validate_annotation_doc
from app.domain.annotation_format import validate_annotation_markup

FULL_JSON_OUTPUT_FORMAT = "rosetta.annotation_doc.v3.1.full_json"
DEFAULT_PROMPT_LANGUAGE = "zh-CN"
SUPPORTED_PROMPT_LANGUAGES = ("zh-CN", "en-US")

ANNOTATION_ASSISTANT_SYSTEM_PROMPTS = {
    "zh-CN": "你是严谨的标注助手，只输出 JSON。",
    "en-US": "You are a rigorous annotation assistant. Output JSON only.",
}
ANNOTATION_ASSISTANT_SYSTEM_PROMPT = ANNOTATION_ASSISTANT_SYSTEM_PROMPTS[DEFAULT_PROMPT_LANGUAGE]

RUNTIME_PROMPT_SECTION_ORDER = (
    "concept_definition",
    "reference_examples",
    "annotation_format",
    "format_example",
    "input_text",
    "task_emphasis",
)
RUNTIME_PROMPT_SECTION_LABELS = {
    "zh-CN": {
        "concept_definition": "概念定义",
        "reference_examples": "相似参考样例（可选，只用于理解边界，不是当前文本答案）",
        "annotation_format": "标注格式",
        "format_example": "通用格式示例（只说明输出格式，不代表当前任务概念）",
        "input_text": "待标注文本",
        "task_emphasis": "任务强调",
    },
    "en-US": {
        "concept_definition": "Concept definition",
        "reference_examples": "Similar reference examples (optional; for boundary understanding only, not the answer for the current text)",
        "annotation_format": "Annotation format",
        "format_example": "Generic format example (format only; not the current task concept)",
        "input_text": "Text to annotate",
        "task_emphasis": "Task emphasis",
    },
}


def normalize_prompt_language(prompt_language: str | None) -> str:
    normalized = str(prompt_language or DEFAULT_PROMPT_LANGUAGE).strip()
    return normalized if normalized in SUPPORTED_PROMPT_LANGUAGES else DEFAULT_PROMPT_LANGUAGE


def annotation_assistant_system_prompt(prompt_language: str | None = None) -> str:
    language = normalize_prompt_language(prompt_language)
    return ANNOTATION_ASSISTANT_SYSTEM_PROMPTS[language]


def build_protocol_instruction(output_format: str, label: str = "Term", prompt_language: str | None = None) -> tuple[str, str]:
    """Return the frozen runtime protocol instruction and a concept-neutral example."""
    language = normalize_prompt_language(prompt_language)
    clean_label = str(label or "Term").strip() or "Term"
    output_format = str(output_format or "").strip()
    if output_format == FULL_JSON_OUTPUT_FORMAT:
        if language == "en-US":
            instruction = """Annotation format:
- Return a JSON object.
- JSON fields are fixed as text, annotation, explanation.
- annotation must be a complete AnnotationDoc JSON object with version, text, layers.
- layers must at least include spans, relations, attributes, comments, document_labels.
- span fields must include id, start, end, text, label, implicit.
- text must exactly match the text to annotate."""
        else:
            instruction = """标注格式：
- 返回一个 JSON object。
- JSON 字段固定为 text、annotation、explanation。
- annotation 必须是完整 AnnotationDoc JSON object，包含 version、text、layers。
- layers 至少包含 spans、relations、attributes、comments、document_labels。
- span 字段必须包含 id、start、end、text、label、implicit。
- text 必须与待标注文本完全一致。"""
        example = {
            "text": "Example source text.",
            "annotation": {
                "version": "3.1",
                "text": "Example source text.",
                "layers": {
                    "spans": [
                        {
                            "id": "s1",
                            "start": 0,
                            "end": 7,
                            "text": "Example",
                            "label": clean_label,
                            "implicit": False,
                        }
                    ],
                    "relations": [],
                    "attributes": [],
                    "comments": [],
                    "document_labels": [],
                },
            },
            "explanation": "Briefly state why the marked span matches the concept.",
        }
    else:
        if language == "en-US":
            instruction = f"""Annotation format:
- Return a JSON object.
- JSON fields are fixed as text, annotation, explanation.
- annotation uses [span]{{{clean_label}}} to mark all target spans.
- If there is no target span, return an empty string for annotation.
- text must exactly match the text to annotate."""
        else:
            instruction = f"""标注格式：
- 返回一个 JSON object。
- JSON 字段固定为 text、annotation、explanation。
- annotation 使用 [span]{{{clean_label}}} 标出所有目标片段。
- 如果没有目标片段，annotation 返回空字符串。
- text 必须与待标注文本完全一致。"""
        example = {
            "text": "Example source text.",
            "annotation": f"[Example]{{{clean_label}}}",
            "explanation": "Briefly state why the marked span matches the concept.",
        }
    return instruction, json.dumps(example, ensure_ascii=False, indent=2)


def build_runtime_annotation_prompt(
    concept_definition: str,
    input_text: str,
    output_format: str = "",
    labels: list[str] | tuple[str, ...] | None = None,
    task_emphasis: str = "",
    reference_examples: list[dict] | tuple[dict, ...] | None = None,
    prompt_language: str | None = None,
) -> str:
    """Build the frozen annotation prompt used by validation and batch annotation."""
    language = normalize_prompt_language(prompt_language)
    labels_by_key = RUNTIME_PROMPT_SECTION_LABELS[language]
    label = next((str(item).strip() for item in labels or [] if str(item).strip()), "Term")
    protocol_instruction, protocol_example = build_protocol_instruction(output_format, label=label, prompt_language=language)
    reference_examples_block = format_reference_examples(reference_examples or [], prompt_language=language)
    if language == "en-US":
        intro = "Annotate the text according to the concept definition."
        emphasis = str(task_emphasis or "").strip() or (
            "Judge every span independently according to the concept definition. Output JSON only; do not output markdown, lists, explanatory paragraphs, or fields outside the schema."
        )
        return f"""{intro}

{labels_by_key["concept_definition"]}:
{str(concept_definition or '').strip()}

{labels_by_key["reference_examples"]}:
{reference_examples_block}

{protocol_instruction}

{labels_by_key["format_example"]}:
{protocol_example}

{labels_by_key["input_text"]}:
{input_text}

{labels_by_key["task_emphasis"]}:
{emphasis}"""

    emphasis = str(task_emphasis or "").strip() or (
        "请根据概念定义独立判断所有应标注片段。只输出 JSON，不要输出 markdown、列表、解释性段落或 schema 外字段。"
    )
    return f"""请根据以下概念定义标注文本。

{labels_by_key["concept_definition"]}：
{str(concept_definition or '').strip()}

{labels_by_key["reference_examples"]}：
{reference_examples_block}

{protocol_instruction}

{labels_by_key["format_example"]}：
{protocol_example}

{labels_by_key["input_text"]}：
{input_text}

{labels_by_key["task_emphasis"]}：
{emphasis}"""


def build_annotation_prompt(concept: dict, input_text: str) -> str:
    """Build the user prompt for annotation request."""
    prompt_language = concept.get("prompt_language") or concept.get("language")
    language = normalize_prompt_language(prompt_language)
    labels = concept.get("labels") or []
    if not labels:
        labels = _labels_from_examples(concept.get("examples", []))
    return build_runtime_annotation_prompt(
        concept_definition=str(concept.get("prompt", "")),
        input_text=input_text,
        output_format=str(concept.get("output_format") or ""),
        labels=labels,
        reference_examples=concept.get("reference_examples") or [],
        prompt_language=language,
        task_emphasis=str(
            concept.get("task_emphasis")
            or (
                "Judge every span independently according to the concept definition. Reference examples only help understand similar boundaries; the generic format example only explains output format. Output JSON only."
                if language == "en-US"
                else "请根据概念定义独立判断所有应标注片段。参考样例只用于理解相似边界，通用格式示例只用于说明输出格式。只输出 JSON。"
            )
        ),
    )


def format_reference_examples(
    examples: list[dict] | tuple[dict, ...], limit: int = 5, prompt_language: str | None = None
) -> str:
    """Format retrieved references in a dedicated prompt slot, separate from concept definition."""
    language = normalize_prompt_language(prompt_language)
    rows = [example for example in examples if isinstance(example, dict)][: max(0, int(limit))]
    if not rows:
        return "None." if language == "en-US" else "无。"
    blocks: list[str] = []
    for index, example in enumerate(rows, start=1):
        text = str(example.get("text", "")).strip()
        annotation = example.get("annotation", "")
        if isinstance(annotation, dict):
            annotation_text = _annotation_doc_to_markup(annotation)
        else:
            annotation_text = str(annotation or "").strip()
        explanation = str(example.get("explanation", "")).strip()
        similarity = example.get("similarity", "")
        if language == "en-US":
            meta = f", similarity {similarity}" if similarity != "" else ""
            lines = [
                f"Reference example {index}{meta}:",
                f"Source text: {text or 'None'}",
                f"Gold annotation: {annotation_text or 'None'}",
            ]
        else:
            meta = f"，相似度 {similarity}" if similarity != "" else ""
            lines = [
                f"参考样例 {index}{meta}：",
                f"原文：{text or '无'}",
                f"标准 annotation：{annotation_text or '无'}",
            ]
        if explanation:
            lines.append(f"Explanation: {explanation}" if language == "en-US" else f"说明：{explanation}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _labels_from_examples(examples: list[dict]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for example in examples:
        annotation = example.get("annotation", "")
        if isinstance(annotation, dict):
            for span in annotation.get("layers", {}).get("spans", []):
                label = str(span.get("label") or "").strip()
                if label and label not in seen:
                    seen.add(label)
                    labels.append(label)
        else:
            for label in _markup_labels(str(annotation or "")):
                if label and label not in seen:
                    seen.add(label)
                    labels.append(label)
    return labels


def _annotation_doc_to_markup(annotation: dict) -> str:
    parts: list[str] = []
    for span in annotation.get("layers", {}).get("spans", []):
        text = str(span.get("text", "")).strip()
        label = str(span.get("label") or "Term").strip() or "Term"
        implicit = bool(span.get("implicit", False))
        if text:
            parts.append(f"[{'!' if implicit else ''}{text}]{{{label}}}")
    return " ".join(parts)


def _markup_labels(annotation: str) -> list[str]:
    labels: list[str] = []
    for chunk in annotation.split("{")[1:]:
        label = chunk.split("}", 1)[0].strip()
        if label:
            labels.append(label)
    return labels


def parse_annotation_response(raw_response: str) -> tuple[dict | None, str | None]:
    """Parse JSON response from model output; return warning when fallback is needed."""
    cleaned = raw_response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return None, f"无法解析JSON响应：{str(e)}，显示原始响应"
    except Exception as e:
        return None, f"处理响应时出错：{str(e)}，显示原始响应"

    required = {"text", "annotation", "explanation"}
    if not required.issubset(parsed.keys()):
        return None, "JSON响应缺少必需字段，显示原始响应"

    if not isinstance(parsed.get("explanation"), str) or not parsed["explanation"].strip():
        return None, "JSON响应 explanation 为空，显示原始响应"

    annotation = parsed.get("annotation")
    if isinstance(annotation, dict):
        ok, reason = validate_annotation_doc(annotation)
        if not ok:
            return None, f"完整 annotation JSON 不符合规范：{reason}，显示原始响应"
        if annotation.get("text") != parsed["text"]:
            return None, "完整 annotation JSON 的 text 与顶层 text 不一致，显示原始响应"
        parsed["annotation"] = annotation
    else:
        annotation_text = str(annotation or "")
        if not annotation_text.strip():
            parsed["annotation"] = make_annotation_doc(parsed["text"], "")
            return parsed, None
        ok, reason = validate_annotation_markup(annotation_text)
        if not ok:
            return None, f"标注格式不符合规范：{reason}，显示原始响应"
        parsed["annotation"] = make_annotation_doc(parsed["text"], annotation_text)
    return parsed, None


def build_history_entry(
    concept_name: str,
    input_text: str,
    annotation_result: str,
    parsed_result: dict | None,
    platform: str | None,
    model: str | None,
    temperature: float,
) -> dict:
    """Build a standardized history record for session storage."""
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "concept": concept_name,
        "text": input_text,
        "annotation": annotation_result,
        "parsed_result": parsed_result,
        "platform": platform,
        "model": model,
        "temperature": temperature,
    }


def build_history_export_filename(now: datetime | None = None) -> str:
    """Build stable filename for annotation history export."""
    dt = now or datetime.now()
    return f"annotation_history_{dt.strftime('%Y%m%d_%H%M%S')}.json"


def build_history_export_json(history: list[dict], now: datetime | None = None) -> str:
    """Build downloadable JSON payload for current annotation history."""
    dt = now or datetime.now()
    payload = {
        "exported_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "history_count": len(history),
        "history": history,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
