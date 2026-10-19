from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.context import ContextBuilder
from app.models import LLMResponse, SessionKey, ToolCall
from app.runtime import AgentRuntime
from app.session_store import JsonSessionStore
from app.service import ChatService
from app.trace import JsonlTraceRecorder
from app.tools.calculator import CalculatorTool
from app.tools.mock_tools import SearchTool, WeatherTool
from app.tools.registry import ToolRegistry
from app.tools.todo import TodoTool
from tests.helpers import FakeLLM


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in (TodoTool(), CalculatorTool(), WeatherTool(), SearchTool()):
        registry.register(tool)
    return registry


def make_service(root: Path, llm: FakeLLM, max_rounds: int = 6) -> tuple[ChatService, JsonSessionStore]:
    runtime = AgentRuntime(llm, make_registry(), ContextBuilder(), JsonlTraceRecorder(root / "traces"), max_rounds)
    store = JsonSessionStore(root / "sessions")
    return ChatService(store, runtime), store


class RuntimeTests(unittest.TestCase):
    def test_direct_answer_needs_one_llm_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            llm = FakeLLM([LLMResponse(content="Hello")])
            service, _ = make_service(Path(directory), llm)
            self.assertEqual("Hello", service.chat("A", "one", "Hi"))
            self.assertEqual(1, len(llm.calls))

    def test_tool_result_is_fed_back_before_final_answer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            llm = FakeLLM([
                LLMResponse(content=None, tool_calls=[ToolCall("call_1", "weather", {"city": "Guangzhou"})]),
                LLMResponse(content="Guangzhou will be cloudy; bring an umbrella."),
            ])
            service, _ = make_service(Path(directory), llm)
            answer = service.chat("A", "weather", "How is Guangzhou weather?")
            self.assertIn("umbrella", answer)
            self.assertEqual(2, len(llm.calls))
            second_messages = llm.calls[1][0]
            self.assertTrue(any(message["role"] == "tool" and "Guangzhou" in message["content"] for message in second_messages))

    def test_follow_up_reuses_prior_conversation_and_tool_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            llm = FakeLLM([
                LLMResponse(None, [ToolCall("weather_1", "weather", {"city": "Guangzhou"})]),
                LLMResponse("It is cloudy."),
                LLMResponse(None, [ToolCall("todo_1", "todo", {"action": "add", "title": "bring umbrella"})]),
                LLMResponse("I added the umbrella reminder."),
            ])
            service, _ = make_service(Path(directory), llm)
            service.chat("A", "weather", "How is Guangzhou weather?")
            service.chat("A", "weather", "Then remind me to bring an umbrella")
            second_turn_context = llm.calls[2][0]
            contents = "\n".join(message.get("content", "") for message in second_turn_context)
            self.assertIn("Mock weather for Guangzhou", contents)
            self.assertIn("It is cloudy.", contents)

    def test_same_user_sessions_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            llm = FakeLLM([
                LLMResponse(None, [ToolCall("c1", "todo", {"action": "add", "title": "bring umbrella"})]),
                LLMResponse("Saved umbrella."),
                LLMResponse(None, [ToolCall("c2", "todo", {"action": "add", "title": "write weekly report"})]),
                LLMResponse("Saved report."),
            ])
            service, store = make_service(Path(directory), llm)
            service.chat("A", "window-1", "Remember to bring an umbrella")
            service.chat("A", "window-2", "Remember to write the weekly report")
            first = store.load(SessionKey("A", "window-1"))
            second = store.load(SessionKey("A", "window-2"))
            self.assertEqual(["bring umbrella"], [item.title for item in first.todos])
            self.assertEqual(["write weekly report"], [item.title for item in second.todos])

    def test_bad_or_unknown_tool_is_returned_to_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            llm = FakeLLM([
                LLMResponse(None, [ToolCall("bad", "not_a_tool", {})]),
                LLMResponse("I cannot use that tool."),
            ])
            service, _ = make_service(Path(directory), llm)
            self.assertIn("cannot", service.chat("A", "one", "Do a thing"))
            self.assertIn("Unknown tool", llm.calls[1][0][-1]["content"])

    def test_max_rounds_stops_infinite_tool_loop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            llm = FakeLLM([
                LLMResponse(None, [ToolCall("one", "search", {"query": "x"})]),
                LLMResponse(None, [ToolCall("two", "search", {"query": "x"})]),
            ])
            service, _ = make_service(Path(directory), llm, max_rounds=2)
            answer = service.chat("A", "one", "search forever")
            self.assertIn("Stopped after 2", answer)

    def test_llm_failure_becomes_safe_response(self) -> None:
        class BrokenLLM:
            def chat(self, messages, tools):
                raise TimeoutError("provider timed out")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = AgentRuntime(BrokenLLM(), make_registry(), ContextBuilder(), JsonlTraceRecorder(root / "traces"))
            service = ChatService(JsonSessionStore(root / "sessions"), runtime)
            answer = service.chat("A", "one", "Hello")
            self.assertIn("failed", answer)
