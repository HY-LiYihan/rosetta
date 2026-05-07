import tempfile
import unittest
from pathlib import Path

from app.infrastructure.debug.runtime import (
    configure_debug,
    is_debug_mode,
    list_debug_log_files,
    log_debug_event,
    log_llm_chat,
    persist_debug_upload,
    read_debug_events,
)


class TestDebugRuntime(unittest.TestCase):
    def test_configure_and_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            configure_debug(enabled=True, runtime_dir=tmp)
            self.assertTrue(is_debug_mode())
            log_debug_event("unit_test_event", {"k": "v"})
            log_llm_chat(
                provider="deepseek",
                model="debug-model",
                messages=[{"role": "system", "content": "system prompt"}, {"role": "user", "content": "user prompt"}],
                temperature=0.1,
                response="assistant response",
                elapsed_seconds=0.5,
            )
            path = persist_debug_upload("sample.json", '{"a":1}')
            self.assertIsNotNone(path)
            self.assertTrue(Path(path).exists())

            logs_dir = Path(tmp) / "logs" / "debug"
            self.assertTrue(logs_dir.exists())
            self.assertTrue(any(p.suffix == ".jsonl" for p in logs_dir.iterdir()))
            log_files = list_debug_log_files(tmp)
            self.assertEqual(len(log_files), 1)
            events = read_debug_events(log_files[0])
            llm_events = [event for event in events if event["event"] == "llm_chat"]
            self.assertEqual(len(llm_events), 1)
            self.assertEqual(llm_events[0]["payload"]["messages"][0]["content"], "system prompt")
            self.assertEqual(llm_events[0]["payload"]["response"], "assistant response")

        configure_debug(enabled=False)


if __name__ == "__main__":
    unittest.main()
