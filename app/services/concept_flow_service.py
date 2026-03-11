from __future__ import annotations

import json

from app.infrastructure.debug import log_debug_event, persist_debug_upload
from app.services.concept_service import (
    build_import_preview,
    create_concept,
    merge_concepts,
    parse_import_json,
    replace_concepts,
    validate_import_payload,
)


def parse_and_preview_import(file_content: str, existing_concepts: list[dict]) -> dict:
    log_debug_event(
        "concept_import_received",
        {"bytes": len(file_content.encode("utf-8")), "existing_count": len(existing_concepts)},
    )
    persist_debug_upload(filename="concept_import.json", content=file_content)

    try:
        imported_data = parse_import_json(file_content)
    except json.JSONDecodeError:
        log_debug_event("concept_import_invalid_json", {"content_preview": file_content[:500]})
        return {"ok": False, "error": {"field": "file", "reason": "不是有效 JSON 文件", "hint": "检查文件编码与 JSON 格式"}}

    is_valid, error_details = validate_import_payload(imported_data)
    if not is_valid:
        log_debug_event("concept_import_validation_failed", {"error": error_details})
        return {"ok": False, "error": error_details}

    ok, preview_error, preview = build_import_preview(imported_data, existing_concepts)
    if not ok:
        log_debug_event("concept_import_preview_failed", {"error": preview_error})
        return {"ok": False, "error": preview_error}

    log_debug_event(
        "concept_import_preview_ok",
        {
            "version": preview["version"],
            "concept_count": preview["concept_count"],
            "duplicate_count": preview["duplicate_count"],
            "auto_fix_count": preview["auto_fix_count"],
        },
    )
    return {"ok": True, "preview": preview}


def apply_import(existing_concepts: list[dict], preview: dict, import_option: str) -> tuple[list[dict], str, str]:
    normalized_imported_concepts = preview["normalized_concepts"]
    if import_option == "替换现有概念":
        next_concepts, message = replace_concepts(normalized_imported_concepts)
    else:
        next_concepts, message = merge_concepts(existing_concepts, normalized_imported_concepts)
    log_debug_event(
        "concept_import_applied",
        {
            "import_option": import_option,
            "before_count": len(existing_concepts),
            "after_count": len(next_concepts),
            "version": preview["version"],
            "message": message,
        },
    )
    return next_concepts, message, preview["version"]


def create_concept_if_valid(existing_concepts: list[dict], name: str, prompt: str, category: str) -> tuple[bool, str, dict | None]:
    if not (name and prompt and category):
        log_debug_event("concept_create_invalid", {"reason": "missing_required_fields", "name": name, "category": category})
        return False, "请填写所有必填字段：概念名称、提示词和分类", None

    existing_names = {c["name"] for c in existing_concepts}
    if name in existing_names:
        log_debug_event("concept_create_invalid", {"reason": "duplicate_name", "name": name})
        return False, f"概念名称 '{name}' 已存在，请使用其他名称", None

    log_debug_event("concept_create_valid", {"name": name, "category": category, "prompt": prompt})
    return True, "", create_concept(name, prompt, category)
