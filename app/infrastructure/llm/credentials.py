from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

from app.infrastructure.llm.providers import PLATFORM_CONFIGS

DEFAULT_SECRETS_PATH = Path(".streamlit/secrets.toml")


@lru_cache(maxsize=4)
def _load_local_secrets(secrets_path: str) -> dict[str, object]:
    path = Path(secrets_path)
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def resolve_api_key(
    platform_id: str,
    env_name: str | None = None,
    secret_name: str | None = None,
    secrets_path: str | Path = DEFAULT_SECRETS_PATH,
) -> str:
    if env_name:
        env_value = os.environ.get(env_name)
        if env_value:
            return env_value

    secrets_dict = _load_local_secrets(str(secrets_path))
    if secret_name:
        secret_value = secrets_dict.get(secret_name)
        if isinstance(secret_value, str) and secret_value.strip():
            return secret_value.strip()

    platform_config = PLATFORM_CONFIGS.get(platform_id)
    if platform_config is not None:
        fallback_secret = secrets_dict.get(platform_config.key_name)
        if isinstance(fallback_secret, str) and fallback_secret.strip():
            return fallback_secret.strip()

    lookup_chain = []
    if env_name:
        lookup_chain.append(f"环境变量 `{env_name}`")
    if secret_name:
        lookup_chain.append(f"`{secrets_path}` 中的 `{secret_name}`")
    if platform_config is not None:
        lookup_chain.append(f"`{secrets_path}` 中的 `{platform_config.key_name}`")
    joined = " 或 ".join(lookup_chain) if lookup_chain else "可用凭据来源"
    raise RuntimeError(f"缺少平台 {platform_id} 的 API Key，请检查 {joined}")
