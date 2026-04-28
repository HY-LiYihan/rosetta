from __future__ import annotations

from app.domain.annotation_format import extract_annotation_tokens

ANNOTATION_DOC_VERSION = "3.1"
_SPAN_REQUIRED = {"id", "start", "end", "text", "label", "implicit"}


def legacy_string_to_spans(source_text: str, annotation_str: str) -> list[dict]:
    tokens = extract_annotation_tokens(annotation_str)
    spans: list[dict] = []
    search_from = 0
    for i, token in enumerate(tokens):
        text = token["text"]
        implicit = token["implicit"]
        if implicit:
            start, end = -1, -1
        else:
            pos = source_text.find(text, search_from)
            if pos != -1:
                start, end = pos, pos + len(text)
                search_from = end
            else:
                start, end = -1, -1
        spans.append({"id": f"s{i}", "start": start, "end": end, "text": text, "label": token["label"], "implicit": implicit})
    return spans


def make_annotation_doc(source_text: str, annotation_str: str, meta: dict | None = None) -> dict:
    return {
        "version": ANNOTATION_DOC_VERSION,
        "text": source_text,
        "layers": {
            "spans": legacy_string_to_spans(source_text, annotation_str),
            "relations": [],
            "attributes": [],
            "comments": [],
            "document_labels": [],
        },
        "provenance": {},
        "meta": meta or {},
    }


def validate_annotation_doc(doc: object) -> tuple[bool, str | None]:
    if not isinstance(doc, dict):
        return False, "annotation 必须为 dict"
    for field in ("version", "text", "layers"):
        if field not in doc:
            return False, f"annotation 缺少必需字段 '{field}'"
    layers = doc.get("layers")
    if not isinstance(layers, dict):
        return False, "annotation.layers 必须为 dict"
    spans = layers.get("spans")
    if not isinstance(spans, list):
        return False, "annotation.layers.spans 必须为 list"
    for i, span in enumerate(spans):
        if not isinstance(span, dict):
            return False, f"spans[{i}] 必须为 dict"
        missing = _SPAN_REQUIRED - span.keys()
        if missing:
            return False, f"spans[{i}] 缺少字段 {missing}"
    return True, None


def spans_to_legacy_string(spans: list[dict]) -> str:
    parts: list[str] = []
    for span in spans:
        text = span["text"]
        label = span["label"]
        prefix = "!" if span.get("implicit") else ""
        parts.append(f"[{prefix}{text}]{{{label}}}")
    return " ".join(parts)
