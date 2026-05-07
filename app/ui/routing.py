from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit


def is_debug_route_url(url: str | None, debug_path: str = "debug") -> bool:
    """Return True when a Streamlit context URL points at the hidden debug page."""
    if not url:
        return False

    raw_url = str(url).strip()
    if not raw_url:
        return False

    parsed = urlsplit(raw_url)
    path = parsed.path or raw_url.split("?", 1)[0].split("#", 1)[0]
    path_parts = [part for part in path.split("/") if part]
    return len(path_parts) == 1 and path_parts[0] == debug_path.strip("/")


def is_debug_route_context(context: Any, debug_path: str = "debug") -> bool:
    """Return True when a Streamlit context object is currently on /debug."""
    return is_debug_route_url(getattr(context, "url", None), debug_path=debug_path)
