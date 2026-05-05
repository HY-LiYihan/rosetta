import threading
import time
import unittest

from app.infrastructure.llm.runtime import DEFAULT_LLM_CONCURRENCY, LLMProviderProfile, LLMServiceRuntime


class DummyProvider:
    def __init__(self):
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def chat(self, api_key, model, messages, temperature=0.3):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.02)
        with self.lock:
            self.active -= 1
        return "ok"


class TestLLMServiceRuntime(unittest.TestCase):
    def test_default_profile_concurrency_is_fifty(self):
        profile = LLMProviderProfile(provider_id="dummy-default-test", model="dummy")

        self.assertEqual(DEFAULT_LLM_CONCURRENCY, 50)
        self.assertEqual(profile.default_concurrency, 50)
        self.assertEqual(profile.max_concurrency, 50)
        self.assertEqual(profile.normalized_concurrency(999), 50)

    def test_map_chat_respects_provider_concurrency_and_records_usage(self):
        provider = DummyProvider()
        runtime = LLMServiceRuntime(
            LLMProviderProfile(provider_id="dummy-runtime-test", model="dummy", default_concurrency=3, max_concurrency=3),
            api_key="test",
            provider=provider,
            concurrency=3,
        )
        calls = [
            {"system_prompt": "system", "messages": [{"role": "user", "content": f"item {index}"}]}
            for index in range(10)
        ]

        results = runtime.map_chat(calls)
        usage = runtime.usage_summary()

        self.assertEqual(len(results), 10)
        self.assertLessEqual(provider.max_active, 3)
        self.assertLessEqual(usage["max_observed_concurrency"], 3)
        self.assertEqual(usage["llm_call_count"], 10)
        self.assertGreater(usage["total_tokens"], 0)
        self.assertTrue(any(event["event_type"] == "call_succeeded" for event in runtime.progress_events))
        succeeded = [event for event in runtime.progress_events if event["event_type"] == "call_succeeded"][0]
        self.assertEqual(succeeded["metadata"]["content"], "[redacted]")

    def test_event_sink_receives_redacted_runtime_events(self):
        provider = DummyProvider()
        sink_events = []
        runtime = LLMServiceRuntime(
            LLMProviderProfile(provider_id="dummy-runtime-sink-test", model="dummy", default_concurrency=2, max_concurrency=2),
            api_key="test",
            provider=provider,
            concurrency=2,
            event_sink=sink_events.append,
        )

        runtime.chat("system", [{"role": "user", "content": "hello"}])

        self.assertTrue(any(event["event_type"] == "call_started" for event in sink_events))
        succeeded = [event for event in sink_events if event["event_type"] == "call_succeeded"][0]
        self.assertEqual(succeeded["metadata"]["content"], "[redacted]")
        self.assertEqual(succeeded["provider"], "dummy-runtime-sink-test")


if __name__ == "__main__":
    unittest.main()
