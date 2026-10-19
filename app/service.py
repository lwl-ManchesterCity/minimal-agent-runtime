from __future__ import annotations

from .models import SessionKey
from .runtime import AgentRuntime
from .session_store import JsonSessionStore


class ChatService:
    def __init__(self, store: JsonSessionStore, runtime: AgentRuntime):
        self.store = store
        self.runtime = runtime

    def chat(self, user_id: str, session_id: str, message: str) -> str:
        state = self.store.load(SessionKey(user_id=user_id, session_id=session_id))
        answer = self.runtime.run(state, message)
        self.store.save(state)
        return answer
