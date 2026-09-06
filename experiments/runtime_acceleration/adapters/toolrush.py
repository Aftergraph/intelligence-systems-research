from __future__ import annotations

from .base import TreatmentSetupError, dispatch_handler

TOOLRUSH_PIN = "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e"


class ToolRushAdapter:
    """Treatment adapter that refuses silent fallback or revision drift."""

    def __init__(self, handlers: dict, *, enabled: bool, actual_revision: str):
        if not enabled:
            raise TreatmentSetupError("ToolRush treatment is not explicitly enabled")
        if actual_revision != TOOLRUSH_PIN:
            raise TreatmentSetupError(
                f"ToolRush revision mismatch: expected {TOOLRUSH_PIN}, got {actual_revision}"
            )
        self._handlers = dict(handlers)
        self.actual_revision = actual_revision

    def execute(self, operation: str, payload: dict) -> dict:
        return dispatch_handler(self._handlers, operation, payload)
