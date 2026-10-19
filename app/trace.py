from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import SessionKey, now_iso


class JsonlTraceRecorder:
    def __init__(self, root: Path):
        self.root = root

    def record(self, key: SessionKey, event: str, **fields: Any) -> None:
        path = self.root / key.user_id / f"{key.session_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        safe = {name: self._truncate(value) for name, value in fields.items()}
        line = {"timestamp": now_iso(), "event": event, **safe}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")

    @staticmethod
    def _truncate(value: Any) -> Any:
        if isinstance(value, str):
            return value[:1000]
        return value
