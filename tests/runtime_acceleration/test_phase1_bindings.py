from __future__ import annotations

from importlib import import_module

import pytest

TOOLRUSH_PIN = "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e"
OBSCURA_PIN = "a1e09de68c7617b8079fbb1661b0548c501971c1"


class _BrowserBackend:
    def __init__(self, name: str):
        self.name = name
        self.calls: list[tuple[str, dict]] = []

    def perform(self, operation: str, payload: dict):
        self.calls.append((operation, dict(payload)))
        return {"browser": self.name, "operation": operation, "payload": dict(payload)}


def _tool_handlers(name: str):
    def handler(operation: str):
        return lambda payload: {"tool": name, "operation": operation, "payload": dict(payload)}

    return {
        "read": handler("read"),
        "search": handler("search"),
        "shell": handler("shell"),
    }


def _bindings():
    module = import_module("experiments.runtime_acceleration.phase1_bindings")
    return module.build_condition_adapter_factory, module.HostBindingError


def _factory(**overrides):
    build, _ = _bindings()
    chromium = overrides.pop("chromium_backend", _BrowserBackend("chromium"))
    obscura = overrides.pop("obscura_backend", _BrowserBackend("obscura"))
    factory = build(
        stock_handlers=_tool_handlers("stock"),
        toolrush_handlers=_tool_handlers("toolrush"),
        toolrush_enabled=True,
        toolrush_revision=TOOLRUSH_PIN,
        chromium_backend=chromium,
        obscura_backend=obscura,
        obscura_revision=OBSCURA_PIN,
        **overrides,
    )
    return factory, chromium, obscura


def test_condition_matrix_binds_exact_tool_and_browser_layers():
    factory, _, _ = _factory()

    expected = {
        "A": ("stock", "chromium"),
        "B": ("toolrush", "chromium"),
        "C": ("stock", "obscura"),
        "D": ("toolrush", "obscura"),
    }
    for condition, (tool_name, browser_name) in expected.items():
        adapter = factory(condition)
        tool = adapter.execute("read", {"path": "fixture/source_a.py"})
        browser = adapter.execute("browser_query", {"selector": "#marker"})
        assert tool["tool"] == tool_name
        assert browser["browser"] == browser_name
        assert browser["operation"] == "query"


def test_browser_prefix_is_removed_and_payload_is_preserved():
    factory, chromium, _ = _factory()
    adapter = factory("A")

    result = adapter.execute("browser_navigate", {"url": "http://127.0.0.1:9999/static"})

    assert result["operation"] == "navigate"
    assert result["payload"] == {"url": "http://127.0.0.1:9999/static"}
    assert chromium.calls == [("navigate", {"url": "http://127.0.0.1:9999/static"})]


def test_unknown_condition_fails_closed():
    factory, _, _ = _factory()
    _, HostBindingError = _bindings()

    with pytest.raises(HostBindingError, match="condition"):
        factory("E")


def test_toolrush_disabled_or_revision_drift_blocks_treated_conditions():
    build, _ = _bindings()
    chromium = _BrowserBackend("chromium")
    obscura = _BrowserBackend("obscura")

    disabled = build(
        stock_handlers=_tool_handlers("stock"),
        toolrush_handlers=_tool_handlers("toolrush"),
        toolrush_enabled=False,
        toolrush_revision=TOOLRUSH_PIN,
        chromium_backend=chromium,
        obscura_backend=obscura,
        obscura_revision=OBSCURA_PIN,
    )
    with pytest.raises(Exception, match="not explicitly enabled"):
        disabled("B")

    drifted = build(
        stock_handlers=_tool_handlers("stock"),
        toolrush_handlers=_tool_handlers("toolrush"),
        toolrush_enabled=True,
        toolrush_revision="0" * 40,
        chromium_backend=chromium,
        obscura_backend=obscura,
        obscura_revision=OBSCURA_PIN,
    )
    with pytest.raises(Exception, match="revision mismatch"):
        drifted("D")


def test_obscura_revision_drift_blocks_obscura_conditions_but_not_control():
    build, _ = _bindings()
    factory = build(
        stock_handlers=_tool_handlers("stock"),
        toolrush_handlers=_tool_handlers("toolrush"),
        toolrush_enabled=True,
        toolrush_revision=TOOLRUSH_PIN,
        chromium_backend=_BrowserBackend("chromium"),
        obscura_backend=_BrowserBackend("obscura"),
        obscura_revision="f" * 40,
    )

    assert factory("A").execute("read", {})["tool"] == "stock"
    with pytest.raises(Exception, match="revision mismatch"):
        factory("C")


def test_missing_browser_backend_fails_when_that_condition_is_constructed():
    build, _ = _bindings()
    factory = build(
        stock_handlers=_tool_handlers("stock"),
        toolrush_handlers=_tool_handlers("toolrush"),
        toolrush_enabled=True,
        toolrush_revision=TOOLRUSH_PIN,
        chromium_backend=None,
        obscura_backend=_BrowserBackend("obscura"),
        obscura_revision=OBSCURA_PIN,
    )

    with pytest.raises(Exception, match="unavailable"):
        factory("A")


def test_tool_operation_never_falls_through_to_browser():
    factory, chromium, _ = _factory()
    adapter = factory("A")

    with pytest.raises(ValueError, match="unsupported operation"):
        adapter.execute("unknown_tool", {})

    assert chromium.calls == []
