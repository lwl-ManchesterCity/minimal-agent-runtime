from __future__ import annotations

import unittest

from app.models import SessionKey, SessionState
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry
from app.tools.todo import TodoTool


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = SessionState(SessionKey("A", "one"))

    def test_calculator_allows_arithmetic_but_not_code(self) -> None:
        tool = CalculatorTool()
        self.assertEqual("14", tool.execute({"expression": "2 * (3 + 4)"}, self.state).content)
        result = tool.execute({"expression": "__import__('os').system('whoami')"}, self.state)
        self.assertFalse(result.ok)
        self.assertEqual("CALCULATION_ERROR", result.error_code)

    def test_todo_is_stateful_within_one_session(self) -> None:
        tool = TodoTool()
        tool.execute({"action": "add", "title": "bring umbrella"}, self.state)
        self.assertIn("bring umbrella", tool.execute({"action": "list"}, self.state).content)
        done = tool.execute({"action": "complete", "todo_id": 1}, self.state)
        self.assertTrue(done.ok)
        self.assertTrue(self.state.todos[0].done)

    def test_registry_rejects_duplicate_names(self) -> None:
        registry = ToolRegistry()
        registry.register(TodoTool())
        with self.assertRaises(ValueError):
            registry.register(TodoTool())
