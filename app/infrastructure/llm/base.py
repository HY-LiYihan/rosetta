from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

ModelFilter = Callable[[list[str]], list[str]]


@dataclass(frozen=True)
class PlatformConfig:
    platform_id: str
    name: str
    base_url: str
    key_name: str
    default_model: str
    model_filter: ModelFilter | None = None


class OpenAICompatibleProvider:
    """Provider for OpenAI-compatible endpoints (DeepSeek/Kimi/Qwen/Zhipu)."""

    def __init__(self, config: PlatformConfig):
        self.config = config

    def get_client(self, api_key: str):
        # Lazy import to keep unit tests independent from runtime package installation.
        from openai import OpenAI

        return OpenAI(api_key=api_key, base_url=self.config.base_url)

    def list_models(self, api_key: str) -> list[str]:
        client = self.get_client(api_key)
        model_list = client.models.list()
        model_ids = [m.id for m in model_list.data]

        if self.config.model_filter is not None:
            model_ids = self.config.model_filter(model_ids)

        return sorted(model_ids)

    def chat(self, api_key: str, model: str, messages: list[dict], temperature: float = 0.3) -> str:
        client = self.get_client(api_key)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=2000,
        )
        return response.choices[0].message.content
