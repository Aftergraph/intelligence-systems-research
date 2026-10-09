from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

_SECRET_KEYS = ("secret", "password", "api_key", "apikey", "authorization", "access_token", "refresh_token", "bearer_token")


def _redact(value: Any, key: str = "") -> Any:
    if any(fragment in key.casefold() for fragment in _SECRET_KEYS):
        return "[REDACTED]"
    if isinstance(value, str):
        value = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s\"']+", r"\1[REDACTED]", value)
        value = re.sub(r"\b(?:sk|ghp|github_pat|ts)_[A-Za-z0-9_-]{8,}\b", "[REDACTED]", value)
        return value
    if isinstance(value, dict):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


class AuditLog:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.events: list[dict[str, Any]] = []
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event_type: str, **payload: Any) -> dict[str, Any]:
        event = {"ts": time.time(), "type": event_type, **_redact(payload)}
        self.events.append(event)
        if self.path:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    record = append
