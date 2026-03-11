import json
from datetime import datetime

from app.domain.annotation_format import validate_annotation_markup


def build_annotation_prompt(concept: dict, input_text: str) -> str:
    """Build the user prompt for annotation request."""
    prompt = f"""你是一个语言学标注助手。请根据以下概念进行文本标注：

概念：{concept['name']}
定义：{concept['prompt']}

标注示例（JSON格式）：
[
"""

    examples_json = []
    for example in concept.get("examples", []):
        example_dict = {
            "text": example["text"],
            "annotation": example["annotation"],
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
- annotation: 标注结果，必须使用 [原文]{{概念标签}} 格式；隐含义使用 [!隐含义]{{概念标签}}
- explanation: 解释说明

返回格式示例：
{{
  "text": "{input_text}",
  "annotation": "[示例词]{{标签}} ... [!隐含义]{{标签}}",
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

    ok, reason = validate_annotation_markup(parsed.get("annotation", ""))
    if not ok:
        return None, f"标注格式不符合规范：{reason}，显示原始响应"

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
