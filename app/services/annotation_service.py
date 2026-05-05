import json
from datetime import datetime

from app.domain.annotation_doc import make_annotation_doc, validate_annotation_doc
from app.domain.annotation_format import validate_annotation_markup

FULL_JSON_OUTPUT_FORMAT = "rosetta.annotation_doc.v3.1.full_json"


def build_protocol_instruction(output_format: str, label: str = "Term") -> tuple[str, str]:
    """Return the frozen runtime protocol instruction and a concept-neutral example."""
    clean_label = str(label or "Term").strip() or "Term"
    output_format = str(output_format or "").strip()
    if output_format == FULL_JSON_OUTPUT_FORMAT:
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
) -> str:
    """Build the frozen annotation prompt used by validation and batch annotation."""
    label = next((str(item).strip() for item in labels or [] if str(item).strip()), "Term")
    protocol_instruction, protocol_example = build_protocol_instruction(output_format, label=label)
    emphasis = str(task_emphasis or "").strip() or (
        "请根据概念定义独立判断所有应标注片段。只输出 JSON，不要输出 markdown、列表、解释性段落或 schema 外字段。"
    )
    return f"""请根据以下概念定义标注文本。

概念定义：
{str(concept_definition or '').strip()}

{protocol_instruction}

通用格式示例（只说明输出格式，不代表当前任务概念）：
{protocol_example}

待标注文本：
{input_text}

任务强调：
{emphasis}"""


def build_annotation_prompt(concept: dict, input_text: str) -> str:
    """Build the user prompt for annotation request."""
    labels = concept.get("labels") or []
    if not labels:
        labels = _labels_from_examples(concept.get("examples", []))
    return build_runtime_annotation_prompt(
        concept_definition=str(concept.get("prompt", "")),
        input_text=input_text,
        output_format=str(concept.get("output_format") or ""),
        labels=labels,
        task_emphasis=str(
            concept.get("task_emphasis")
            or "请根据概念定义独立判断所有应标注片段。参考样例只用于理解相似边界，通用格式示例只用于说明输出格式。只输出 JSON。"
        ),
    )


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
