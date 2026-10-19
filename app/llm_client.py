from __future__ import annotations

import json
import os
from typing import Protocol

from .models import LLMResponse, ToolCall


class LLMClient(Protocol):
    def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


class DeepSeekClient:
    """Thin provider adapter; the runtime does not depend on the OpenAI SDK directly."""

    def __init__(self, api_key: str | None = None, model: str | None = None, thinking: bool = False):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.thinking = thinking or os.getenv("DEEPSEEK_THINKING", "false").lower() == "true"
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is required. Put it in your shell environment, not in this repository.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install dependencies first: pip install -e .") from exc
        self._client = OpenAI(api_key=self.api_key, base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        kwargs = {"model": self.model, "messages": messages, "tools": tools}
        if self.thinking:
            kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
        completion = self._client.chat.completions.create(**kwargs)
        message = completion.choices[0].message
        calls: list[ToolCall] = []
        for call in message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments)
            except json.JSONDecodeError:
                # Preserve malformed input for the runtime error path.
                arguments = {"__invalid_json__": call.function.arguments}
            calls.append(ToolCall(id=call.id, name=call.function.name, arguments=arguments))
        return LLMResponse(
            content=message.content,
            tool_calls=calls,
            reasoning_content=getattr(message, "reasoning_content", None),
        )
