from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .jev_client import SystemOneResponse, Usage


class ScriptedDecisionBackend:
    """Deterministic decision backend used for tests and offline reproductions."""

    def __init__(self, responses: Iterable[dict[str, Any]]) -> None:
        self._responses = iter(responses)
        self.requests: list[dict[str, Any]] = []

    def system_one(self, *, state: Any, questions: dict[str, dict[str, Any]], model: str | None = None) -> SystemOneResponse:
        self.requests.append({"state": state, "questions": questions, "model": model})
        payload = next(self._responses)
        usage = payload.get("usage") or {}
        return SystemOneResponse(
            model=str(payload.get("model", "scripted")),
            answers=dict(payload.get("answers") or {}),
            usage=Usage(
                input_tokens=int(usage.get("input_tokens", 0) or 0),
                output_tokens=int(usage.get("output_tokens", 0) or 0),
            ),
            raw=payload,
        )
