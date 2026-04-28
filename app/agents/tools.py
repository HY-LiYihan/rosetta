from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

ToolHandler = Callable[["ToolInvocation"], dict[str, Any]]


@dataclass(frozen=True)
class ToolInvocation:
    name: str
    state: dict[str, Any]
    input: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: ToolHandler


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None):
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if not tool.name.strip():
            raise ValueError("tool.name must be non-empty")
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._tools)

    def run(self, name: str, state: dict[str, Any], input: dict[str, Any] | None = None) -> dict[str, Any]:
        tool = self.get(name)
        return tool.handler(ToolInvocation(name=name, state=state, input=input or {}))
