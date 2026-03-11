from __future__ import annotations

import json

from app.services.concept_service import (
    build_import_preview,
    create_concept,
    merge_concepts,
    parse_import_json,
    replace_concepts,
    validate_import_payload,
)


def parse_and_preview_import(file_content: str, existing_concepts: list[dict]) -> dict:
    try:
        imported_data = parse_import_json(file_content)
    except json.JSONDecodeError:
        return {"ok": False, "error": {"field": "file", "reason": "不是有效 JSON 文件", "hint": "检查文件编码与 JSON 格式"}}

    is_valid, error_details = validate_import_payload(imported_data)
    if not is_valid:
        return {"ok": False, "error": error_details}

    ok, preview_error, preview = build_import_preview(imported_data, existing_concepts)
    if not ok:
        return {"ok": False, "error": preview_error}

    return {"ok": True, "preview": preview}


def apply_import(existing_concepts: list[dict], preview: dict, import_option: str) -> tuple[list[dict], str, str]:
    normalized_imported_concepts = preview["normalized_concepts"]
    if import_option == "替换现有概念":
        next_concepts, message = replace_concepts(normalized_imported_concepts)
    else:
        next_concepts, message = merge_concepts(existing_concepts, normalized_imported_concepts)
    return next_concepts, message, preview["version"]


def create_concept_if_valid(existing_concepts: list[dict], name: str, prompt: str, category: str) -> tuple[bool, str, dict | None]:
    if not (name and prompt and category):
        return False, "请填写所有必填字段：概念名称、提示词和分类", None

    existing_names = {c["name"] for c in existing_concepts}
    if name in existing_names:
        return False, f"概念名称 '{name}' 已存在，请使用其他名称", None

    return True, "", create_concept(name, prompt, category)
