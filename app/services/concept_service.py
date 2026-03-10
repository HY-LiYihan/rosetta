import json
from app.domain.schemas import DATA_VERSION
from app.domain.validators import ImportValidationError, normalize_payload


def build_export_json(concepts: list[dict]) -> str:
    """Serialize concepts to pretty JSON for download."""
    return json.dumps({"version": DATA_VERSION, "concepts": concepts}, ensure_ascii=False, indent=2)


def parse_import_json(raw_content: str) -> dict:
    """Parse uploaded JSON text payload."""
    return json.loads(raw_content)


def validate_import_payload(payload: dict) -> tuple[bool, dict | None]:
    """Validate concepts import payload and normalize to stable schema."""
    try:
        normalize_payload(payload)
    except ImportValidationError as e:
        return False, {"field": e.field, "reason": e.reason, "hint": e.hint}
    except Exception as e:
        return False, {"field": "unknown", "reason": str(e), "hint": "检查导入 JSON 的结构与字段类型"}
    return True, None


def replace_concepts(imported_concepts: list[dict]) -> tuple[list[dict], str]:
    """Replace existing concepts with imported concepts."""
    normalized = normalize_payload({"concepts": imported_concepts})["concepts"]
    return normalized, f"✅ 成功替换为 {len(normalized)} 个概念"


def merge_concepts(existing_concepts: list[dict], imported_concepts: list[dict]) -> tuple[list[dict], str]:
    """Append non-duplicate concepts from import payload."""
    normalized_imported = normalize_payload({"concepts": imported_concepts})["concepts"]
    existing_names = {c["name"] for c in existing_concepts}
    new_concepts = []
    duplicate_count = 0

    for concept in normalized_imported:
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
