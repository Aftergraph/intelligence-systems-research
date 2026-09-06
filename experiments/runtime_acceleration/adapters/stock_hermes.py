from __future__ import annotations

from .base import dispatch_handler


class StockHermesAdapter:
    """Control-path adapter whose host handlers invoke stock Hermes operations."""

    def __init__(self, handlers: dict):
        self._handlers = dict(handlers)

    def execute(self, operation: str, payload: dict) -> dict:
        return dispatch_handler(self._handlers, operation, payload)
