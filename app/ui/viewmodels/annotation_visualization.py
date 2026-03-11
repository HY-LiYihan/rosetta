from __future__ import annotations

import html
from hashlib import md5

from app.domain.annotation_format import TOKEN_PATTERN

_PALETTE = [
    ("#5B8FF9", "#EAF1FF"),
    ("#61DDAA", "#E9FBF4"),
    ("#65789B", "#EEF2F8"),
    ("#F6BD16", "#FFF8E6"),
    ("#7262FD", "#F1EEFF"),
    ("#78D3F8", "#EAF9FF"),
    ("#9661BC", "#F4ECFA"),
    ("#F6903D", "#FFF3EB"),
    ("#008685", "#E8F8F8"),
    ("#F08BB4", "#FDEFF5"),
]


def _label_color(label: str) -> tuple[str, str]:
    idx = int(md5(label.encode("utf-8")).hexdigest(), 16) % len(_PALETTE)
    return _PALETTE[idx]


def annotation_to_colored_html(annotation_text: str) -> str:
    if not annotation_text:
        return ""

    parts: list[str] = []
    last_end = 0
    for match in TOKEN_PATTERN.finditer(annotation_text):
        start, end = match.span()
        raw_text = match.group(1).strip()
        label = match.group(2).strip()
        implicit = raw_text.startswith("!")
        visible_text = raw_text[1:].strip() if implicit else raw_text

        if start > last_end:
            parts.append(html.escape(annotation_text[last_end:start]))

        text_color, bg_color = _label_color(label)
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
