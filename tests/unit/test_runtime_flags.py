import unittest

from app.infrastructure.config.runtime_flags import parse_runtime_flags


class TestRuntimeFlags(unittest.TestCase):
    def test_parse_from_arg(self):
        flags = parse_runtime_flags(["--debug"], {})
        self.assertTrue(flags.debug_mode)

    def test_parse_from_env(self):
        flags = parse_runtime_flags([], {"ROSETTA_DEBUG_MODE": "true"})
        self.assertTrue(flags.debug_mode)

    def test_parse_default_false(self):
        flags = parse_runtime_flags([], {})
        self.assertFalse(flags.debug_mode)


if __name__ == "__main__":
    unittest.main()
