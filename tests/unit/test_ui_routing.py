import unittest
from types import SimpleNamespace

from app.ui.routing import is_debug_route_context, is_debug_route_url


class UIRoutingTests(unittest.TestCase):
    def test_debug_route_matches_direct_debug_url(self):
        self.assertTrue(is_debug_route_url("http://localhost:8501/debug"))
        self.assertTrue(is_debug_route_url("http://localhost:8501/debug?event=llm_chat"))
        self.assertTrue(is_debug_route_url("/debug#latest"))

    def test_debug_route_rejects_main_and_similar_paths(self):
        self.assertFalse(is_debug_route_url("http://localhost:8501/"))
        self.assertFalse(is_debug_route_url("http://localhost:8501/debugger"))
        self.assertFalse(is_debug_route_url("http://localhost:8501/foo/debug"))
        self.assertFalse(is_debug_route_url(""))
        self.assertFalse(is_debug_route_url(None))

    def test_debug_route_context_uses_context_url(self):
        self.assertTrue(is_debug_route_context(SimpleNamespace(url="http://localhost:8501/debug")))
        self.assertFalse(is_debug_route_context(SimpleNamespace(url="http://localhost:8501/")))
        self.assertFalse(is_debug_route_context(SimpleNamespace()))


if __name__ == "__main__":
    unittest.main()
