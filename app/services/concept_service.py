import json


def build_export_json(concepts: list[dict]) -> str:
    """Serialize concepts to pretty JSON for download."""
    return json.dumps({"concepts": concepts}, ensure_ascii=False, indent=2)


def parse_import_json(raw_content: str) -> dict:
    """Parse uploaded JSON text payload."""
    return json.loads(raw_content)


def validate_import_payload(payload: dict) -> tuple[bool, str]:
    """Validate concepts import payload schema at a minimal level."""
    if "concepts" not in payload or not isinstance(payload["concepts"], list):
        return False, "文件格式错误：缺少 'concepts' 字段或格式不正确"
    return True, ""


def replace_concepts(imported_concepts: list[dict]) -> tuple[list[dict], str]:
    """Replace existing concepts with imported concepts."""
    return imported_concepts, f"✅ 成功替换为 {len(imported_concepts)} 个概念"


def merge_concepts(existing_concepts: list[dict], imported_concepts: list[dict]) -> tuple[list[dict], str]:
    """Append non-duplicate concepts from import payload."""
    existing_names = {c["name"] for c in existing_concepts}
    new_concepts = []
    duplicate_count = 0

    for concept in imported_concepts:
        if concept["name"] not in existing_names:
            new_concepts.append(concept)
        else:
            duplicate_count += 1

    merged = existing_concepts + new_concepts
    message = f"✅ 成功添加 {len(new_concepts)} 个新概念"
    if duplicate_count > 0:
        message += f"，跳过了 {duplicate_count} 个重复概念"

    return merged, message


def create_concept(name: str, prompt: str, category: str) -> dict:
    """Build a new concept object from user input."""
    return {
        "name": name,
        "prompt": prompt,
        "examples": [],
        "category": category,
        "is_default": False,
    }
