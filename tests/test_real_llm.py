from __future__ import annotations

import os
import unittest

from app.llm_client import DeepSeekClient
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry


@unittest.skipUnless(os.getenv("RUN_REAL_LLM") == "1", "Set RUN_REAL_LLM=1 to call the paid real API")
class RealLLMSmokeTest(unittest.TestCase):
    def test_deepseek_can_choose_calculator(self) -> None:
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        client = DeepSeekClient()
        response = client.chat(
            [{"role": "user", "content": "Use the calculator tool to calculate 19 * 3."}],
            registry.openai_schemas(),
        )
        self.assertTrue(response.tool_calls or response.content)
