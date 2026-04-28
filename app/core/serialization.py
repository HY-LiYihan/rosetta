from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def to_plain_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_plain_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [to_plain_dict(item) for item in value]
    if isinstance(value, list):
        return [to_plain_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain_dict(item) for key, item in value.items()}
    return value
