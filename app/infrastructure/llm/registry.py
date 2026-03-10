from __future__ import annotations

from app.infrastructure.llm.base import OpenAICompatibleProvider
from app.infrastructure.llm.providers import PLATFORM_CONFIGS


def get_platform_configs() -> dict[str, dict]:
    """Expose legacy-compatible config dict for UI layers."""
    return {
        pid: {
            "name": cfg.name,
            "url": cfg.base_url,
            "key_name": cfg.key_name,
            "default_model": cfg.default_model,
        }
        for pid, cfg in PLATFORM_CONFIGS.items()
    }


def get_provider(platform_id: str) -> OpenAICompatibleProvider | None:
    cfg = PLATFORM_CONFIGS.get(platform_id)
    if cfg is None:
        return None
    return OpenAICompatibleProvider(cfg)
