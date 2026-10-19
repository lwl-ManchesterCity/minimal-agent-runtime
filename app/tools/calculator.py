from __future__ import annotations

import ast
import operator

from ..models import SessionState, ToolResult
from .registry import Tool


class CalculatorTool(Tool):
    name = "calculator"
    description = "Safely calculate a mathematical expression using numbers and + - * / ** parentheses."
    parameters_schema = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
        "additionalProperties": False,
    }
    _operators = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def execute(self, arguments: dict, state: SessionState) -> ToolResult:
        try:
            tree = ast.parse(arguments["expression"], mode="eval")
            value = self._evaluate(tree.body)
            return ToolResult(True, str(value))
        except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
            return ToolResult(False, f"Cannot calculate expression: {exc}", "CALCULATION_ERROR")

    def _evaluate(self, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in self._operators:
            return self._operators[type(node.op)](self._evaluate(node.left), self._evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._operators:
            return self._operators[type(node.op)](self._evaluate(node.operand))
        raise ValueError("only numeric arithmetic is allowed")
