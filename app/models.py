from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SessionKey:
    user_id: str
    session_id: str


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatMessage:
    role: str
    content: str | None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatMessage":
        calls = [ToolCall(**call) for call in data.get("tool_calls", [])]
        return cls(
            role=data["role"], content=data.get("content"),
            tool_call_id=data.get("tool_call_id"), tool_calls=calls,
        )


@dataclass
class TodoItem:
    id: int
    title: str
    done: bool = False
    created_at: str = field(default_factory=now_iso)


@dataclass
class SessionState:
    key: SessionKey
    messages: list[ChatMessage] = field(default_factory=list)
    todos: list[TodoItem] = field(default_factory=list)
    rolling_summary: str = ""
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": asdict(self.key),
            "messages": [message.to_dict() for message in self.messages],
            "todos": [asdict(todo) for todo in self.todos],
            "rolling_summary": self.rolling_summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        return cls(
            key=SessionKey(**data["key"]),
            messages=[ChatMessage.from_dict(item) for item in data.get("messages", [])],
            todos=[TodoItem(**item) for item in data.get("todos", [])],
            rolling_summary=data.get("rolling_summary", ""),
            created_at=data.get("created_at", now_iso()),
            updated_at=data.get("updated_at", now_iso()),
        )


@dataclass
class ToolResult:
    ok: bool
    content: str
    error_code: str | None = None


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning_content: str | None = None
