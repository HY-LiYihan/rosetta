import json
from datetime import datetime

from app.domain.annotation_doc import make_annotation_doc, spans_to_legacy_string, validate_annotation_doc
from app.domain.annotation_format import validate_annotation_markup

FULL_JSON_OUTPUT_FORMAT = "rosetta.annotation_doc.v3.1.full_json"


def build_annotation_prompt(concept: dict, input_text: str) -> str:
    """Build the user prompt for annotation request."""
    output_format = str(concept.get("output_format") or "").strip()
    use_full_json = output_format == FULL_JSON_OUTPUT_FORMAT
    annotation_rule = (
        """- annotation: 完整 AnnotationDoc JSON object，必须包含 version、text、layers；layers 至少包含 spans、relations、attributes、comments、document_labels。"""
        if use_full_json
        else "- annotation: 标注结果，必须使用 [原文]{概念标签} 格式；隐含义使用 [!隐含义]{概念标签}"
    )
    annotation_example = {
        "version": "3.1",
        "text": input_text,
        "layers": {
            "spans": [
                {
                    "id": "s1",
                    "start": 0,
                    "end": 3,
                    "text": "示例词",
                    "label": "Term",
                    "implicit": False,
                }
            ],
            "relations": [],
            "attributes": [],
            "comments": [],
            "document_labels": [],
        },
    } if use_full_json else "[示例词]{标签} ... [!隐含义]{标签}"
    prompt = f"""你是一个语言学标注助手。请根据以下概念进行文本标注：

概念：{concept['name']}
定义：{concept['prompt']}

标注示例（JSON格式）：
[
"""

    examples_json = []
    for example in concept.get("examples", []):
        ann = example["annotation"]
        if isinstance(ann, dict):
            ann = spans_to_legacy_string(ann.get("layers", {}).get("spans", []))
        example_dict = {
            "text": example["text"],
            "annotation": ann,
            "explanation": example.get("explanation", ""),
        }
        examples_json.append(json.dumps(example_dict, ensure_ascii=False))

    prompt += ",\n".join(examples_json)
    prompt += f"""
]

现在请标注以下文本：
文本：\"{input_text}\"

请以JSON格式返回标注结果，只包含JSON，不要有其他文本。JSON应包含以下字段：
- text: 原始文本
{annotation_rule}
- explanation: 解释说明

返回格式示例：
{{
  "text": "{input_text}",
  "annotation": {json.dumps(annotation_example, ensure_ascii=False)},
  "explanation": "解释说明..."
}}"""

    return prompt


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
        ok, reason = validate_annotation_markup(str(annotation or ""))
        if not ok:
            return None, f"标注格式不符合规范：{reason}，显示原始响应"
        parsed["annotation"] = make_annotation_doc(parsed["text"], str(annotation))
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
