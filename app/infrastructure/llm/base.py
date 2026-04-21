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
    chat_extra_body: dict[str, object] | None = None


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
        extra_body = dict(self.config.chat_extra_body or {})
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=2000,
            extra_body=extra_body or None,
        )
        message = response.choices[0].message
        content = message.content
        if isinstance(content, list):
            text_chunks: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_chunks.append(str(item.get("text", "")))
                elif hasattr(item, "text"):
                    text_chunks.append(str(item.text))
            content = "".join(text_chunks)
        if isinstance(content, str) and content.strip():
            return content

        reasoning_content = getattr(message, "reasoning_content", None)
        if isinstance(reasoning_content, str) and reasoning_content.strip():
            return reasoning_content
        return ""

    def embed(
        self,
        api_key: str,
        model: str,
        inputs: list[str],
        dimensions: int | None = None,
    ) -> list[list[float]]:
        client = self.get_client(api_key)
        params: dict[str, object] = {
            "model": model,
            "input": inputs,
        }
        if dimensions is not None:
            params["dimensions"] = dimensions
        response = client.embeddings.create(**params)
        return [item.embedding for item in response.data]
