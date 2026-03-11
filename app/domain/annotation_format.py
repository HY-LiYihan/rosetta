from __future__ import annotations

import re

TOKEN_PATTERN = re.compile(r"\[([^\[\]]+)\]\{([^{}]+)\}")
LEGACY_TOKEN_PATTERN = re.compile(r"\[[^\[\]]+\]\s*\([^)]+\)")


def extract_annotation_tokens(annotation_text: str) -> list[dict]:
    tokens: list[dict] = []
    for match in TOKEN_PATTERN.finditer(annotation_text):
        raw_text = match.group(1).strip()
        label = match.group(2).strip()
        implicit = raw_text.startswith("!")
        text = raw_text[1:].strip() if implicit else raw_text
        tokens.append({"text": text, "label": label, "implicit": implicit})
    return tokens


def validate_annotation_markup(annotation_text: str) -> tuple[bool, str | None]:
    if not isinstance(annotation_text, str) or not annotation_text.strip():
        return False, "annotation 不能为空且必须为字符串"

    if LEGACY_TOKEN_PATTERN.search(annotation_text):
        return False, "检测到旧格式 [文本](标签)，请改为 [文本]{标签}"

    tokens = extract_annotation_tokens(annotation_text)
    if not tokens:
        return False, "annotation 至少包含一个 [文本]{标签} 标注片段"

    for token in tokens:
        if not token["label"]:
            return False, "标签不能为空，格式应为 [文本]{标签}"
        if not token["text"]:
            if token["implicit"]:
                return False, "隐含标注格式应为 [!隐含义]{标签}，! 后必须有内容"
            return False, "标注文本不能为空，格式应为 [文本]{标签}"

    return True, None
