from __future__ import annotations

from .models import ChatMessage, SessionState


SYSTEM_PROMPT = """You are a helpful assistant. Use tools when they provide needed facts or when
the user asks to manage session todos. If the user asks you to remember, remind them, add a todo,
or keep track of an action, you MUST call todo with action=add before your final answer. A written
reminder in the final answer is not a substitute for a persisted todo. Use todo with action=list
when the user asks for their current todos. Do not claim to have executed a tool unless a tool
result is present. Answer concisely after the necessary tool calls."""


class ContextBuilder:
    def __init__(self, keep_recent_messages: int = 12, compact_after_messages: int = 16):
        self.keep_recent_messages = keep_recent_messages
        self.compact_after_messages = compact_after_messages

    def build(self, state: SessionState) -> list[dict]:
        self._compact_if_needed(state)
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        active = [f"#{todo.id}: {todo.title}" for todo in state.todos if not todo.done]
        if active:
            messages.append({"role": "system", "content": "Active session todos:\n" + "\n".join(active)})
        if state.rolling_summary:
            messages.append({"role": "system", "content": "Earlier conversation summary:\n" + state.rolling_summary})
        messages.extend(self._as_api_message(message) for message in state.messages[-self.keep_recent_messages:])
        return messages

    @staticmethod
    def _as_api_message(message: ChatMessage) -> dict:
        result = {"role": message.role, "content": message.content or ""}
        if message.tool_call_id:
            result["tool_call_id"] = message.tool_call_id
        if message.tool_calls:
            result["tool_calls"] = [
                {"id": call.id, "type": "function", "function": {
                    "name": call.name, "arguments": __import__("json").dumps(call.arguments, ensure_ascii=False),
                }}
                for call in message.tool_calls
            ]
        return result

    def _compact_if_needed(self, state: SessionState) -> None:
        if len(state.messages) <= self.compact_after_messages:
            return
        old = state.messages[:-self.keep_recent_messages]
        summary_items = [self._summarize(message) for message in old]
        new_summary = " ".join(item for item in summary_items if item)
        state.rolling_summary = (state.rolling_summary + " " + new_summary).strip()[-4000:]
        state.messages = state.messages[-self.keep_recent_messages:]

    @staticmethod
    def _summarize(message: ChatMessage) -> str:
        text = (message.content or "").replace("\n", " ").strip()[:240]
        if message.role == "user":
            return f"User said: {text}"
        if message.role == "tool":
            return f"Tool result: {text}"
        if message.role == "assistant" and message.tool_calls:
            return "Assistant requested tools: " + ", ".join(call.name for call in message.tool_calls)
        if message.role == "assistant":
            return f"Assistant replied: {text}"
        return ""
