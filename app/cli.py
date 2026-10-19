from __future__ import annotations

import argparse
from pathlib import Path

from .context import ContextBuilder
from .llm_client import DeepSeekClient
from .runtime import AgentRuntime
from .service import ChatService
from .session_store import JsonSessionStore
from .trace import JsonlTraceRecorder
from .tools.calculator import CalculatorTool
from .tools.mock_tools import SearchTool, WeatherTool
from .tools.registry import ToolRegistry
from .tools.todo import TodoTool


def build_service(data_dir: Path) -> ChatService:
    registry = ToolRegistry()
    for tool in (TodoTool(), CalculatorTool(), WeatherTool(), SearchTool()):
        registry.register(tool)
    runtime = AgentRuntime(
        llm=DeepSeekClient(), registry=registry, context_builder=ContextBuilder(),
        traces=JsonlTraceRecorder(data_dir / "traces"),
    )
    return ChatService(JsonSessionStore(data_dir / "sessions"), runtime)


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal framework-free Agent Runtime")
    parser.add_argument("message", help="The user message")
    parser.add_argument("--user", required=True, help="User identifier")
    parser.add_argument("--session", required=True, help="Independent conversation/window identifier")
    parser.add_argument("--data-dir", default="data", help="Directory for sessions and traces")
    args = parser.parse_args()
    service = build_service(Path(args.data_dir))
    print(service.chat(args.user, args.session, args.message))


if __name__ == "__main__":
    main()
