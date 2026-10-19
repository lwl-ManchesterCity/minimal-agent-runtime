from __future__ import annotations

from ..models import SessionState, TodoItem, ToolResult
from .registry import Tool


class TodoTool(Tool):
    name = "todo"
    description = "Manage todos in the current session. Use add, list, or complete."
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "list", "complete"]},
            "title": {"type": "string"},
            "todo_id": {"type": "integer"},
        },
        "required": ["action"],
        "additionalProperties": False,
    }

    def execute(self, arguments: dict, state: SessionState) -> ToolResult:
        action = arguments["action"]
        if action == "list":
            if not state.todos:
                return ToolResult(True, "No todos in this session.")
            content = "\n".join(
                f"#{item.id} [{'x' if item.done else ' '}] {item.title}" for item in state.todos
            )
            return ToolResult(True, content)
        if action == "add":
            title = arguments.get("title", "").strip()
            if not title:
                return ToolResult(False, "title is required for action=add", "INVALID_ARGUMENTS")
            item = TodoItem(id=max((todo.id for todo in state.todos), default=0) + 1, title=title)
            state.todos.append(item)
            return ToolResult(True, f"Added todo #{item.id}: {item.title}")
        todo_id = arguments.get("todo_id")
        if todo_id is None:
            return ToolResult(False, "todo_id is required for action=complete", "INVALID_ARGUMENTS")
        for item in state.todos:
            if item.id == todo_id:
                item.done = True
                return ToolResult(True, f"Completed todo #{item.id}: {item.title}")
        return ToolResult(False, f"Todo #{todo_id} does not exist", "NOT_FOUND")
