from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable

from app.infrastructure.llm.credentials import resolve_api_key
from app.infrastructure.llm.registry import get_provider

DEFAULT_LLM_CONCURRENCY = 20

_SEMAPHORE_LOCK = threading.Lock()
_PROVIDER_SEMAPHORES: dict[str, threading.BoundedSemaphore] = {}


@dataclass(frozen=True)
class LLMProviderProfile:
    provider_id: str
    model: str
    default_concurrency: int = DEFAULT_LLM_CONCURRENCY
    max_concurrency: int = DEFAULT_LLM_CONCURRENCY
    timeout_seconds: int = 60
    max_retries: int = 2
    retry_backoff_seconds: float = 0.5
    supports_usage: bool = False
    cost_table: dict[str, float] = field(default_factory=dict)

    def normalized_concurrency(self, requested: int | None = None) -> int:
        value = self.default_concurrency if requested is None else requested
        return max(1, min(int(value), int(self.max_concurrency), DEFAULT_LLM_CONCURRENCY))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LLMCallResult:
    index: int
    content: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated: bool
    elapsed_seconds: float
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LLMServiceRuntime:
    def __init__(
        self,
        profile: LLMProviderProfile,
        api_key: str | None = None,
        provider: Any | None = None,
        concurrency: int | None = None,
        event_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.profile = profile
        self.api_key = api_key
        self.provider = provider
        self.concurrency = profile.normalized_concurrency(concurrency)
        self.event_sink = event_sink
        self.progress_events: list[dict[str, Any]] = []
        self.call_results: list[LLMCallResult] = []
        self._state_lock = threading.Lock()
        self._running = 0
        self.max_observed_concurrency = 0

    @classmethod
    def from_provider(
        cls,
        provider_id: str,
        model: str,
        concurrency: int | None = None,
        event_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> "LLMServiceRuntime":
        profile = LLMProviderProfile(provider_id=provider_id, model=model)
        return cls(
            profile=profile,
            api_key=resolve_api_key(provider_id),
            provider=get_provider(provider_id),
            concurrency=concurrency,
            event_sink=event_sink,
        )

    def chat(self, system_prompt: str, messages: list[dict], temperature: float = 0.3, metadata: dict[str, Any] | None = None) -> str:
        return self.chat_result(0, system_prompt, messages, temperature, metadata).content

    def chat_result(
        self,
        index: int,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.3,
        metadata: dict[str, Any] | None = None,
    ) -> LLMCallResult:
        semaphore = _provider_semaphore(self.profile.provider_id, self.profile.max_concurrency)
        self._event("call_queued", index=index, metadata=metadata or {})
        with semaphore:
            return self._call_with_retries(index, system_prompt, messages, temperature, metadata or {})

    def map_chat(
        self,
        calls: Iterable[dict[str, Any]],
        temperature: float = 0.3,
        concurrency: int | None = None,
    ) -> list[LLMCallResult]:
        call_list = list(calls)
        if not call_list:
            return []
        max_workers = max(1, min(self.profile.normalized_concurrency(concurrency or self.concurrency), len(call_list)))
        results: list[LLMCallResult | None] = [None] * len(call_list)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {
                pool.submit(
                    self.chat_result,
                    index,
                    str(call.get("system_prompt", "")),
                    list(call.get("messages", [])),
                    float(call.get("temperature", temperature)),
                    dict(call.get("metadata", {})),
                ): index
                for index, call in enumerate(call_list)
            }
            for future in as_completed(future_map):
                index = future_map[future]
                results[index] = future.result()
        return [result for result in results if result is not None]

    def usage_summary(self) -> dict[str, Any]:
        with self._state_lock:
            results = list(self.call_results)
        prompt_tokens = sum(result.prompt_tokens for result in results)
        completion_tokens = sum(result.completion_tokens for result in results)
        return {
            "provider": self.profile.provider_id,
            "model": self.profile.model,
            "llm_call_count": len(results),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "estimated": True,
            "provider_elapsed_seconds": round(sum(result.elapsed_seconds for result in results), 4),
            "max_observed_concurrency": self.max_observed_concurrency,
            "concurrency": self.concurrency,
        }

    def _call_with_retries(
        self,
        index: int,
        system_prompt: str,
        messages: list[dict],
        temperature: float,
        metadata: dict[str, Any],
    ) -> LLMCallResult:
        error: Exception | None = None
        for retry_count in range(self.profile.max_retries + 1):
            started = time.perf_counter()
            self._mark_started(index, metadata, retry_count)
            try:
                if self.provider is None:
                    raise RuntimeError(f"Unknown LLM provider: {self.profile.provider_id}")
                content = self.provider.chat(
                    api_key=str(self.api_key or ""),
                    model=self.profile.model,
                    messages=[{"role": "system", "content": system_prompt}, *messages],
                    temperature=temperature,
                )
                elapsed = time.perf_counter() - started
                prompt_tokens = _estimate_tokens(system_prompt + "\n" + "\n".join(str(message.get("content", "")) for message in messages))
                completion_tokens = _estimate_tokens(content)
                result = LLMCallResult(
                    index=index,
                    content=content,
                    provider=self.profile.provider_id,
                    model=self.profile.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    estimated=True,
                    elapsed_seconds=round(elapsed, 4),
                    retry_count=retry_count,
                    metadata=metadata,
                )
                self._mark_finished("call_succeeded", result, metadata)
                return result
            except Exception as exc:
                error = exc
                self._event("call_failed", index=index, metadata={**metadata, "error": str(exc), "retry_count": retry_count})
                if retry_count < self.profile.max_retries:
                    time.sleep(self.profile.retry_backoff_seconds * (2**retry_count))
                    self._event("call_retried", index=index, metadata={**metadata, "retry_count": retry_count + 1})
            finally:
                self._mark_stopped()
        assert error is not None
        raise error

    def _mark_started(self, index: int, metadata: dict[str, Any], retry_count: int) -> None:
        with self._state_lock:
            self._running += 1
            self.max_observed_concurrency = max(self.max_observed_concurrency, self._running)
            running = self._running
        self._event("call_started", index=index, metadata={**metadata, "retry_count": retry_count, "running": running})

    def _mark_stopped(self) -> None:
        with self._state_lock:
            self._running = max(0, self._running - 1)

    def _mark_finished(self, event_type: str, result: LLMCallResult, metadata: dict[str, Any]) -> None:
        with self._state_lock:
            self.call_results.append(result)
        result_metadata = result.to_dict()
        result_metadata["content"] = "[redacted]"
        self._event(event_type, index=result.index, metadata={**metadata, **result_metadata})

    def _event(self, event_type: str, index: int, metadata: dict[str, Any]) -> None:
        event: dict[str, Any]
        with self._state_lock:
            event_index = len(self.progress_events) + 1
            completed = len(self.call_results)
            running = self._running
            event = {
                "event_index": event_index,
                "event_type": event_type,
                "provider": self.profile.provider_id,
                "model": self.profile.model,
                "item_index": index,
                "completed": completed,
                "running": running,
                "metadata": metadata,
                "created_at": time.time(),
            }
            self.progress_events.append(event)
        if self.event_sink is not None:
            try:
                self.event_sink(dict(event))
            except Exception:
                pass


def _provider_semaphore(provider_id: str, max_concurrency: int) -> threading.BoundedSemaphore:
    with _SEMAPHORE_LOCK:
        if provider_id not in _PROVIDER_SEMAPHORES:
            _PROVIDER_SEMAPHORES[provider_id] = threading.BoundedSemaphore(max(1, min(max_concurrency, DEFAULT_LLM_CONCURRENCY)))
        return _PROVIDER_SEMAPHORES[provider_id]


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(str(text or "")) / 4))
