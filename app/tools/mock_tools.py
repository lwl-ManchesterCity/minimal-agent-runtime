from __future__ import annotations

from ..models import SessionState, ToolResult
from .registry import Tool


class WeatherTool(Tool):
    name = "weather"
    description = "Get mock weather for a city and date. Use this when a user asks about weather."
    parameters_schema = {
        "type": "object",
        "properties": {"city": {"type": "string"}, "date": {"type": "string"}},
        "required": ["city"], "additionalProperties": False,
    }

    def execute(self, arguments: dict, state: SessionState) -> ToolResult:
        city = arguments["city"]
        date = arguments.get("date", "today")
        return ToolResult(True, f"Mock weather for {city} on {date}: cloudy, 24°C, 60% chance of rain.")


class SearchTool(Tool):
    name = "search"
    description = "Search a local mock index for general information. Results may be incomplete."
    parameters_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"], "additionalProperties": False,
    }

    def execute(self, arguments: dict, state: SessionState) -> ToolResult:
        query = arguments["query"]
        return ToolResult(True, f"Mock search results for '{query}': result 1, result 2. Verify externally before relying on it.")
