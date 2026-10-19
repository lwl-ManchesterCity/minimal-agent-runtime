from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from app.context import ContextBuilder
from app.llm_client import load_project_env
from app.models import ChatMessage, SessionKey, SessionState
from app.session_store import JsonSessionStore


class ContextAndStoreTests(unittest.TestCase):
    def test_context_compacts_old_messages_and_keeps_recent(self) -> None:
        state = SessionState(SessionKey("A", "long"))
        state.messages = [ChatMessage("user", f"message {number}") for number in range(18)]
        builder = ContextBuilder(keep_recent_messages=4, compact_after_messages=6)
        context = builder.build(state)
        self.assertEqual(4, len(state.messages))
        self.assertIn("message 0", state.rolling_summary)
        self.assertTrue(any(message["content"] == "message 17" for message in context))

    def test_store_persists_and_reloads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JsonSessionStore(Path(directory))
            key = SessionKey("A", "one")
            state = store.load(key)
            state.messages.append(ChatMessage("user", "hello"))
            store.save(state)
            self.assertEqual("hello", store.load(key).messages[0].content)

    def test_dotenv_loads_key_without_overwriting_shell_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("DEEPSEEK_API_KEY=file-key\nDEEPSEEK_MODEL='test-model'\n", encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                load_project_env(path)
                import os
                self.assertEqual("file-key", os.environ["DEEPSEEK_API_KEY"])
                os.environ["DEEPSEEK_API_KEY"] = "shell-key"
                load_project_env(path)
                self.assertEqual("shell-key", os.environ["DEEPSEEK_API_KEY"])
