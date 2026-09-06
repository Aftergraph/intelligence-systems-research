from __future__ import annotations

from typing import Protocol


class TreatmentSetupError(RuntimeError):
    """Raised when a treatment cannot be activated exactly as preregistered."""


class ToolAdapter(Protocol):
    def execute(self, operation: str, payload: dict) -> dict: ...


def dispatch_handler(handlers: dict, operation: str, payload: dict) -> dict:
    try:
        handler = handlers[operation]
    except KeyError as exc:
        raise ValueError(f"unsupported operation: {operation}") from exc
    result = handler(payload)
    if not isinstance(result, dict):
        raise TypeError("tool handler must return a mapping")
    return result
