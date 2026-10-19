from __future__ import annotations

import json
import time
import uuid

from .context import ContextBuilder
from .llm_client import LLMClient
from .models import ChatMessage, LLMResponse, SessionState, ToolCall, ToolResult
from .trace import JsonlTraceRecorder
from .tools.registry import ToolRegistry


class AgentRuntime:
    def __init__(self, llm: LLMClient, registry: ToolRegistry, context_builder: ContextBuilder,
                 traces: JsonlTraceRecorder, max_tool_rounds: int = 6):
        self.llm = llm
        self.registry = registry
        self.context_builder = context_builder
        self.traces = traces
        self.max_tool_rounds = max_tool_rounds

    def run(self, state: SessionState, user_message: str) -> str:
        run_id = str(uuid.uuid4())
        state.messages.append(ChatMessage(role="user", content=user_message))
        api_messages = self.context_builder.build(state)
        schemas = self.registry.openai_schemas()

        for round_no in range(1, self.max_tool_rounds + 1):
            started = time.perf_counter()
            try:
                response = self.llm.chat(api_messages, schemas)
            except Exception as exc:  # Provider failure is normalized for the caller.
                self.traces.record(state.key, "llm_error", run_id=run_id, round=round_no, error=str(exc))
                return "The language model request failed. Please retry this message."
            self.traces.record(
                state.key, "llm_response", run_id=run_id, round=round_no,
                latency_ms=int((time.perf_counter() - started) * 1000),
                tool_call_count=len(response.tool_calls),
                reasoning_present=bool(response.reasoning_content),
                reasoning_chars=len(response.reasoning_content or ""),
            )
            if not response.tool_calls:
                answer = response.content or "I could not produce a final answer."
                state.messages.append(ChatMessage(role="assistant", content=answer))
                return answer

            assistant_api = self._assistant_api_message(response)
            api_messages.append(assistant_api)
            # Deliberately omit raw reasoning from persisted session history.
            state.messages.append(ChatMessage(role="assistant", content=response.content, tool_calls=response.tool_calls))
            for call in response.tool_calls:
                result = self._execute(call, state, run_id, round_no)
                tool_message = ChatMessage(role="tool", content=result.content, tool_call_id=call.id)
                state.messages.append(tool_message)
                api_messages.append({"role": "tool", "tool_call_id": call.id, "content": result.content})

        self.traces.record(state.key, "max_tool_rounds_exceeded", run_id=run_id, max_rounds=self.max_tool_rounds)
        return f"Stopped after {self.max_tool_rounds} tool rounds to avoid an infinite loop."

    def _execute(self, call: ToolCall, state: SessionState, run_id: str, round_no: int) -> ToolResult:
        if "__invalid_json__" in call.arguments:
            result = ToolResult(False, "Tool arguments were not valid JSON.", "INVALID_ARGUMENTS")
        else:
            tool = self.registry.get(call.name)
            if tool is None:
                result = ToolResult(False, f"Unknown tool: {call.name}", "UNKNOWN_TOOL")
            else:
                validation_error = self.registry.validate(tool, call.arguments)
                if validation_error:
                    result = ToolResult(False, validation_error, "INVALID_ARGUMENTS")
                else:
                    started = time.perf_counter()
                    try:
                        result = tool.execute(call.arguments, state)
                    except Exception as exc:
                        result = ToolResult(False, f"Tool execution failed: {exc}", "TOOL_EXECUTION_ERROR")
                    latency = int((time.perf_counter() - started) * 1000)
                    self.traces.record(state.key, "tool_finished", run_id=run_id, round=round_no,
                                       tool_name=call.name, tool_call_id=call.id, arguments=call.arguments,
                                       ok=result.ok, error_code=result.error_code, latency_ms=latency,
                                       result_preview=result.content)
                    return result
        self.traces.record(state.key, "tool_rejected", run_id=run_id, round=round_no,
                           tool_name=call.name, tool_call_id=call.id, arguments=call.arguments,
                           ok=False, error_code=result.error_code, result_preview=result.content)
        return result

    @staticmethod
    def _assistant_api_message(response: LLMResponse) -> dict:
        message = {
            "role": "assistant", "content": response.content or "",
            "tool_calls": [{"id": call.id, "type": "function", "function": {
                "name": call.name, "arguments": json.dumps(call.arguments, ensure_ascii=False),
            }} for call in response.tool_calls],
        }
        if response.reasoning_content:
            message["reasoning_content"] = response.reasoning_content
        return message
