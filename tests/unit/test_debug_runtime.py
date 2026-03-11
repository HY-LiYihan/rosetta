import tempfile
import unittest
from pathlib import Path

from app.infrastructure.debug.runtime import (
    configure_debug,
    is_debug_mode,
    log_debug_event,
    persist_debug_upload,
)


class TestDebugRuntime(unittest.TestCase):
    def test_configure_and_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            configure_debug(enabled=True, runtime_dir=tmp)
            self.assertTrue(is_debug_mode())
            log_debug_event("unit_test_event", {"k": "v"})
            path = persist_debug_upload("sample.json", '{"a":1}')
            self.assertIsNotNone(path)
            self.assertTrue(Path(path).exists())

            logs_dir = Path(tmp) / "logs" / "debug"
            self.assertTrue(logs_dir.exists())
            self.assertTrue(any(p.suffix == ".jsonl" for p in logs_dir.iterdir()))

        configure_debug(enabled=False)


if __name__ == "__main__":
    unittest.main()
