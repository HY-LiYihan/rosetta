import unittest

from app.agents.context import ContextChunk, ContextEngine
from app.agents.kernel import AgentKernel
from app.agents.tools import Tool, ToolRegistry


class TestAgentsKernel(unittest.TestCase):
    def test_agent_kernel_runs_registered_tools(self):
        registry = ToolRegistry(
            [
                Tool("first", "first step", lambda invocation: {"value": 1}),
                Tool("second", "second step", lambda invocation: {"value": invocation.state["value"] + 1}),
            ]
        )
        result = AgentKernel().run("test", context={}, tools=registry, tool_plan=["first", "second"])
        self.assertTrue(result.ok)
        self.assertEqual(result.state["value"], 2)
        self.assertEqual(len(result.steps), 2)
        self.assertEqual(result.run.status, "succeeded")

    def test_context_engine_respects_budget(self):
        pack = ContextEngine(budget_chars=20, fresh_tail_chars=10).build_pack(
            goal="g",
            fresh_text="abcdefghijk",
            retrieved=[ContextChunk(id="r1", text="x" * 100, score=1.0)],
        )
        self.assertLessEqual(len(pack.text), 80)
        self.assertIn("fresh_tail", pack.text)


if __name__ == "__main__":
    unittest.main()
