from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .adapters.chromium import ChromiumAdapter
from .adapters.obscura import ObscuraAdapter
from .adapters.stock_hermes import StockHermesAdapter
from .adapters.toolrush import ToolRushAdapter


class HostBindingError(RuntimeError):
    """Raised when a preregistered Phase-1 condition cannot be bound exactly."""


@dataclass(frozen=True)
class BoundTraceAdapter:
    """Route frozen trace operations to exactly one tool layer and one browser layer."""

    condition: str
    tool_layer: object
    browser_layer: object

    def execute(self, operation: str, payload: dict) -> dict:
        if operation.startswith("browser_"):
            browser_operation = operation.removeprefix("browser_")
            if not browser_operation:
                raise HostBindingError("empty browser operation")
            result = self.browser_layer.perform(browser_operation, dict(payload))
        else:
            result = self.tool_layer.execute(operation, dict(payload))
        if not isinstance(result, dict):
            raise TypeError("bound treatment operation must return a mapping")
        return result


def build_condition_adapter_factory(
    *,
    stock_handlers: dict,
    toolrush_handlers: dict,
    toolrush_enabled: bool,
    toolrush_revision: str,
    chromium_backend,
    obscura_backend,
    obscura_revision: str,
) -> Callable[[str], BoundTraceAdapter]:
    """Return the exact A/B/C/D treatment factory for the preregistered 2x2 study.

    Construction is deliberately lazy. A control condition does not require a treatment
    dependency that it does not use, while any requested treatment still fails closed on
    disabled lanes, revision drift, or an unavailable browser backend. No fallback path
    exists in this layer.
    """
    frozen_stock_handlers = dict(stock_handlers)
    frozen_toolrush_handlers = dict(toolrush_handlers)

    def make_tool_layer(condition: str):
        if condition in {"A", "C"}:
            return StockHermesAdapter(frozen_stock_handlers)
        if condition in {"B", "D"}:
            return ToolRushAdapter(
                frozen_toolrush_handlers,
                enabled=bool(toolrush_enabled),
                actual_revision=str(toolrush_revision),
            )
        raise HostBindingError(f"unknown Phase-1 condition: {condition}")

    def make_browser_layer(condition: str):
        if condition in {"A", "B"}:
            return ChromiumAdapter(chromium_backend)
        if condition in {"C", "D"}:
            return ObscuraAdapter(obscura_backend, actual_revision=str(obscura_revision))
        raise HostBindingError(f"unknown Phase-1 condition: {condition}")

    def factory(condition: str) -> BoundTraceAdapter:
        normalized = str(condition).strip().upper()
        if normalized not in {"A", "B", "C", "D"}:
            raise HostBindingError(f"unknown Phase-1 condition: {condition}")
        tool_layer = make_tool_layer(normalized)
        browser_layer = make_browser_layer(normalized)
        return BoundTraceAdapter(
            condition=normalized,
            tool_layer=tool_layer,
            browser_layer=browser_layer,
        )

    return factory
