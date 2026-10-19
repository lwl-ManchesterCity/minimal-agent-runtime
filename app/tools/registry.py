from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import SessionState, ToolResult


class Tool(ABC):
    name: str
    description: str
    parameters_schema: dict[str, Any]

    @abstractmethod
    def execute(self, arguments: dict[str, Any], state: SessionState) -> ToolResult:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool name: {tool.name}")
        if tool.parameters_schema.get("type") != "object":
            raise ValueError(f"Tool {tool.name} must use an object JSON Schema")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def openai_schemas(self) -> list[dict[str, Any]]:
        return [
            {"type": "function", "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema,
            }}
            for tool in self._tools.values()
        ]

    def validate(self, tool: Tool, arguments: dict[str, Any]) -> str | None:
        schema = tool.parameters_schema
        if not isinstance(arguments, dict):
            return "arguments must be a JSON object"
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for name in required:
            if name not in arguments:
                return f"missing required parameter: {name}"
        if schema.get("additionalProperties") is False:
            extras = set(arguments) - set(properties)
            if extras:
                return f"unexpected parameters: {', '.join(sorted(extras))}"
        for name, value in arguments.items():
            expected = properties.get(name, {}).get("type")
            if expected == "string" and not isinstance(value, str):
                return f"parameter {name} must be a string"
            if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
                return f"parameter {name} must be an integer"
            enum = properties.get(name, {}).get("enum")
            if enum is not None and value not in enum:
                return f"parameter {name} must be one of {enum}"
        return None
