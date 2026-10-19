from __future__ import annotations

import json
from pathlib import Path

from .models import SessionKey, SessionState, now_iso


class SessionCorruptedError(RuntimeError):
    pass


class JsonSessionStore:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, key: SessionKey) -> Path:
        if "/" in key.user_id or "/" in key.session_id:
            raise ValueError("user_id and session_id cannot contain '/'")
        return self.root / key.user_id / f"{key.session_id}.json"

    def load(self, key: SessionKey) -> SessionState:
        path = self._path(key)
        if not path.exists():
            return SessionState(key=key)
        try:
            return SessionState.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise SessionCorruptedError(f"Cannot read session: {path}") from exc

    def save(self, state: SessionState) -> None:
        path = self._path(state.key)
        path.parent.mkdir(parents=True, exist_ok=True)
        state.updated_at = now_iso()
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(path)
