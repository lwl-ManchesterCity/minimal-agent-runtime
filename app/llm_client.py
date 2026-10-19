from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from .models import LLMResponse, ToolCall


class LLMClient(Protocol):
    def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


def load_project_env(path: Path | None = None) -> None:
    """Load simple KEY=VALUE settings from .env without overwriting shell variables."""
    env_path = path or Path.cwd() / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


class DeepSeekClient:
    """Thin provider adapter; the runtime does not depend on the OpenAI SDK directly."""

    def __init__(self, api_key: str | None = None, model: str | None = None, thinking: bool = False):
        load_project_env()
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
