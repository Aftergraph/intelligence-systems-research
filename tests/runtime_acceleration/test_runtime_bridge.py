from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest

TOOLRUSH_PIN = "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e"
OBSCURA_PIN = "a1e09de68c7617b8079fbb1661b0548c501971c1"


def _bridge():
    return import_module("experiments.runtime_acceleration.runtime_bridge")


def _surface(mode: str) -> dict:
    symbols = {
        "tools.file_tools.read_file_tool": {"status": "READY", "signature": "(path, offset=1, limit=2000, task_id='default')"},
        "tools.file_tools.search_tool": {"status": "READY", "signature": "(pattern, target='content', path='.', **kwargs)"},
        "tools.environments.local.LocalEnvironment": {"status": "READY", "signature": "(cwd, timeout=120, env=None)"},
        "tools.file_operations.ShellFileOperations": {"status": "READY", "signature": "(env)"},
    }
    return {
        "mode": mode,
        "symbols": symbols,
        "toolrush_plugin_loaded": mode == "toolrush",
        "toolrush_flags": {
            "TOOLRUSH_FASTLANE": "1" if mode == "toolrush" else "0",
            "TOOLRUSH_SEARCH": "1" if mode == "toolrush" else "0",
            "TOOLRUSH_PERSIST": "1" if mode == "toolrush" else "0",
        },
    }


def test_worker_argv_uses_real_hermes_python_and_plugin_only_for_treatment():
    bridge = _bridge()
    config = {
        "hermes_python": r"C:\hermes\.venv\Scripts\python.exe",
        "hermes_root": r"C:\hermes",
        "workspace": r"C:\Aftergraph\JAR-EXP-0013\workspace",
        "toolrush_plugin": r"C:\hermes\plugins\toolrush\__init__.py",
    }

    stock = bridge.build_hermes_worker_argv(config, "stock")
    treated = bridge.build_hermes_worker_argv(config, "toolrush")

    assert stock[:4] == [config["hermes_python"], "-u", "-m", "experiments.runtime_acceleration.hermes_host_worker"]
    assert "--hermes-root" in stock and config["hermes_root"] in stock
    assert "--workspace" in stock and config["workspace"] in stock
    assert "--toolrush-plugin" not in stock
    assert treated[-2:] == ["--toolrush-plugin", config["toolrush_plugin"]]
    assert "--mode" in treated and "toolrush" in treated


def test_surface_validation_requires_real_hermes_symbols_and_treatment_plugin():
    bridge = _bridge()

    assert bridge.validate_surface_report(_surface("stock"), "stock")["mode"] == "stock"
    assert bridge.validate_surface_report(_surface("toolrush"), "toolrush")["toolrush_plugin_loaded"] is True

    broken = _surface("stock")
    broken["symbols"].pop("tools.file_tools.search_tool")
    with pytest.raises(bridge.RuntimeBridgeError, match="search_tool"):
        bridge.validate_surface_report(broken, "stock")

    unpatched = _surface("toolrush")
    unpatched["toolrush_plugin_loaded"] = False
    with pytest.raises(bridge.RuntimeBridgeError, match="plugin"):
        bridge.validate_surface_report(unpatched, "toolrush")


def test_surface_validation_rejects_acceleration_flag_drift():
    bridge = _bridge()
    stock = _surface("stock")
    stock["toolrush_flags"]["TOOLRUSH_SEARCH"] = "1"
    with pytest.raises(bridge.RuntimeBridgeError, match="TOOLRUSH_SEARCH"):
        bridge.validate_surface_report(stock, "stock")

    treated = _surface("toolrush")
    treated["toolrush_flags"]["TOOLRUSH_PERSIST"] = "0"
    with pytest.raises(bridge.RuntimeBridgeError, match="TOOLRUSH_PERSIST"):
        bridge.validate_surface_report(treated, "toolrush")


def test_fixture_url_is_loopback_only_and_scheme_is_resolved_deterministically():
    bridge = _bridge()

    assert bridge.resolve_fixture_url("fixture://static", "http://127.0.0.1:43123") == "http://127.0.0.1:43123/static"
    assert bridge.resolve_fixture_url("fixture://form?value=alpha", "http://127.0.0.1:43123") == "http://127.0.0.1:43123/form?value=alpha"
    assert bridge.resolve_fixture_url("http://127.0.0.1:43123/static", "http://127.0.0.1:43123") == "http://127.0.0.1:43123/static"

    with pytest.raises(bridge.RuntimeBridgeError, match="loopback"):
        bridge.resolve_fixture_url("https://example.com", "http://127.0.0.1:43123")


class _Worker:
    def __init__(self, name: str):
        self.name = name
        self.calls: list[tuple[str, dict]] = []

    def execute(self, operation: str, payload: dict) -> dict:
        self.calls.append((operation, dict(payload)))
        return {"worker": self.name, "operation": operation, "payload": dict(payload)}

    def handlers(self) -> dict:
        return {
            operation: (lambda payload, op=operation: self.execute(op, payload))
            for operation in ("read", "search", "shell")
        }


class _Browser:
    def __init__(self, name: str, serial: int):
        self.name = name
        self.serial = serial
        self.calls: list[tuple[str, dict]] = []

    def perform(self, operation: str, payload: dict) -> dict:
        self.calls.append((operation, dict(payload)))
        return {"browser": self.name, "serial": self.serial, "operation": operation, "payload": dict(payload)}


class _BrowserFactory:
    def __init__(self, name: str):
        self.name = name
        self.created: list[_Browser] = []

    def __call__(self):
        backend = _Browser(self.name, len(self.created) + 1)
        self.created.append(backend)
        return backend


def test_runtime_factory_feeds_real_worker_surfaces_into_frozen_matrix():
    bridge = _bridge()
    stock = _Worker("stock")
    toolrush = _Worker("toolrush")
    chromium = _BrowserFactory("chromium")
    obscura = _BrowserFactory("obscura")

    factory = bridge.build_runtime_adapter_factory(
        stock_worker=stock,
        toolrush_worker=toolrush,
        chromium_backend_factory=chromium,
        obscura_backend_factory=obscura,
        toolrush_revision=TOOLRUSH_PIN,
        obscura_revision=OBSCURA_PIN,
    )

    expected = {
        "A": ("stock", "chromium"),
        "B": ("toolrush", "chromium"),
        "C": ("stock", "obscura"),
        "D": ("toolrush", "obscura"),
    }
    for condition, (tool_name, browser_name) in expected.items():
        adapter = factory(condition)
        assert adapter.execute("read", {"path": "fixture/source_a.py"})["worker"] == tool_name
        assert adapter.execute("browser_query", {"selector": "#deterministic-marker"})["browser"] == browser_name

    assert len(chromium.created) == 2
    assert len(obscura.created) == 2


def test_each_adapter_construction_gets_a_fresh_browser_backend():
    bridge = _bridge()
    chromium = _BrowserFactory("chromium")
    obscura = _BrowserFactory("obscura")
    factory = bridge.build_runtime_adapter_factory(
        stock_worker=_Worker("stock"),
        toolrush_worker=_Worker("toolrush"),
        chromium_backend_factory=chromium,
        obscura_backend_factory=obscura,
        toolrush_revision=TOOLRUSH_PIN,
        obscura_revision=OBSCURA_PIN,
    )

    first = factory("A").execute("browser_query", {"selector": "#x"})
    second = factory("A").execute("browser_query", {"selector": "#x"})

    assert first["serial"] == 1
    assert second["serial"] == 2


def test_runtime_factory_refuses_unvalidated_treatment_revision():
    bridge = _bridge()
    with pytest.raises(Exception, match="revision mismatch"):
        bridge.build_runtime_adapter_factory(
            stock_worker=_Worker("stock"),
            toolrush_worker=_Worker("toolrush"),
            chromium_backend_factory=_BrowserFactory("chromium"),
            obscura_backend_factory=_BrowserFactory("obscura"),
            toolrush_revision="0" * 40,
            obscura_revision=OBSCURA_PIN,
        )("B")
