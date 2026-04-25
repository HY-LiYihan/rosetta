from __future__ import annotations

import html

from app.domain.annotation_format import TOKEN_PATTERN

BASE_GREEN_HUE = 142  # darker green base
COLOR_SATURATION = 65
COLOR_LIGHTNESS = 40
WHITE_BG = "#FFFFFF"


def _format_hsl(hue: float) -> str:
    return f"hsl({int(round(hue))}, {COLOR_SATURATION}%, {COLOR_LIGHTNESS}%)"


def _build_hues(label_count: int) -> list[float]:
    if label_count <= 0:
        return []
    if label_count == 1:
        return [BASE_GREEN_HUE]
    if label_count == 2:
        # Explicitly satisfy the requested pair: green + red.
        return [BASE_GREEN_HUE, 0]

    # Keep first color as green; distribute remaining hues evenly.
    # For small counts, prioritize warm hues (orange/yellow family).
    if label_count <= 4:
        remain = label_count - 1
        start, end = 30, 60
        step = (end - start) / (remain - 1) if remain > 1 else 0
        warm_hues = [start + i * step for i in range(remain)]
        return [BASE_GREEN_HUE] + warm_hues

    remain = label_count - 1
    span = 300
    step = span / (remain - 1)
    other_hues = [0 + i * step for i in range(remain)]
    return [BASE_GREEN_HUE] + other_hues


def _build_label_color_map(labels: list[str]) -> dict[str, tuple[str, str]]:
    hues = _build_hues(len(labels))
    mapping: dict[str, tuple[str, str]] = {}
    for label, hue in zip(labels, hues):
        color = _format_hsl(hue)
        mapping[label] = (color, WHITE_BG)
    return mapping


def annotation_to_colored_html(annotation_text) -> str:
    if not annotation_text:
        return ""
    if isinstance(annotation_text, dict):
        from app.domain.annotation_doc import spans_to_legacy_string
        annotation_text = spans_to_legacy_string(annotation_text.get("layers", {}).get("spans", []))
    if not annotation_text:
        return ""

    labels_in_order: list[str] = []
    for match in TOKEN_PATTERN.finditer(annotation_text):
        label = match.group(2).strip()
        if label and label not in labels_in_order:
            labels_in_order.append(label)
    color_map = _build_label_color_map(labels_in_order)

    parts: list[str] = []
    last_end = 0
    for match in TOKEN_PATTERN.finditer(annotation_text):
        start, end = match.span()
        raw_text = match.group(1).strip()
        label = match.group(2).strip()
        implicit = raw_text.startswith("!")  # kept for format compatibility
        visible_text = raw_text[1:].strip() if implicit else raw_text

        if start > last_end:
            parts.append(html.escape(annotation_text[last_end:start]))

        text_color, bg_color = color_map.get(label, (_format_hsl(BASE_GREEN_HUE), WHITE_BG))
        label_suffix = f"|{label}"
        token_html = (
            f'<span '
            f'style="display:inline-block;padding:0 0.35rem;border-radius:0.35rem;'
            f'border:1px solid {text_color};background:{bg_color};color:{text_color};'
            f'font-weight:600;cursor:help;line-height:1.6;">'
            f'{html.escape(visible_text)}</span>'
            f'<span style="color:{text_color};font-weight:600;margin-left:0.2rem;line-height:1.6;">'
            f'{html.escape(label_suffix)}</span>'
        )
        parts.append(token_html)
        last_end = end

    if last_end < len(annotation_text):
        parts.append(html.escape(annotation_text[last_end:]))

    return "".join(parts)
