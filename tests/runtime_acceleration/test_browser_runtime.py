from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest


def _runtime():
    return import_module("experiments.runtime_acceleration.browser_runtime")


class _Response:
    status = 200


class _Locator:
    def __init__(self, count=1, text="deterministic-marker"):
        self._count = count
        self._text = text

    def count(self):
        return self._count

    @property
    def first(self):
        return self

    def text_content(self):
        return self._text


class _Page:
    def __init__(self):
        self.url = "about:blank"
        self.goto_calls = []
        self.evaluate_calls = []
        self.screenshot_calls = []
        self.locators = {}

    def goto(self, url, **kwargs):
        self.goto_calls.append((url, dict(kwargs)))
        self.url = url
        return _Response()

    def locator(self, selector):
        return self.locators.get(selector, _Locator())

    def evaluate(self, script):
        self.evaluate_calls.append(script)
        return {"value": 7}

    def screenshot(self, **kwargs):
        self.screenshot_calls.append(dict(kwargs))
        return b"png"


class _Context:
    def __init__(self, page=None):
        self.page = page or _Page()
        self.closed = False

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


class _Browser:
    def __init__(self, context=None):
        self.context = context or _Context()
        self.contexts = [self.context]
        self.closed = False

    def new_context(self):
        self.context = _Context()
        self.contexts = [self.context]
        return self.context

    def close(self):
        self.closed = True


class _Chromium:
    def __init__(self):
        self.launch_calls = []
        self.connect_calls = []
        self.launch_browser = _Browser()
        self.cdp_browser = _Browser()

    def launch(self, **kwargs):
        self.launch_calls.append(dict(kwargs))
        return self.launch_browser

    def connect_over_cdp(self, endpoint, **kwargs):
        self.connect_calls.append((endpoint, dict(kwargs)))
        return self.cdp_browser


class _Playwright:
    def __init__(self):
        self.chromium = _Chromium()
        self.stopped = False

    def stop(self):
        self.stopped = True


class _Starter:
    def __init__(self):
        self.instances = []

    def __call__(self):
        item = _Playwright()
        self.instances.append(item)
        return item


class _Process:
    def __init__(self):
        self.returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


def test_obscura_serve_argv_is_loopback_and_allows_local_fixture_network():
    runtime = _runtime()
    argv = runtime.build_obscura_runtime_argv(r"C:\obscura\obscura.exe", 43190)
    assert argv == [
        "C:/obscura/obscura.exe",
        "serve",
        "--port",
        "43190",
        "--host",
        "127.0.0.1",
        "--allow-private-network",
    ]


def test_page_backend_resolves_fixture_navigation_and_rejects_external_hosts(tmp_path):
    runtime = _runtime()
    page = _Page()
    closed = []
    backend = runtime.PlaywrightPageBackend(
        page,
        fixture_base_url="http://127.0.0.1:43123",
        close_callback=lambda: closed.append(True),
        evidence_root=tmp_path,
    )

    result = backend.perform("navigate", {"url": "fixture://static"})
    assert page.goto_calls == [
        ("http://127.0.0.1:43123/static", {"wait_until": "domcontentloaded"})
    ]
    assert result == {"url": "http://127.0.0.1:43123/static", "status": 200}

    with pytest.raises(runtime.BrowserRuntimeError, match="loopback"):
        backend.perform("navigate", {"url": "https://example.com"})

    backend.perform("close", {})
    assert closed == [True]


def test_page_backend_query_evaluate_and_screenshot_are_stable(tmp_path):
    runtime = _runtime()
    page = _Page()
    page.locators["#missing"] = _Locator(count=0, text=None)
    backend = runtime.PlaywrightPageBackend(
        page,
        fixture_base_url="http://127.0.0.1:43123",
        close_callback=lambda: None,
        evidence_root=tmp_path,
    )

    assert backend.perform("query", {"selector": "#deterministic-marker"}) == {
        "selector": "#deterministic-marker",
        "count": 1,
        "text": "deterministic-marker",
    }
    assert backend.perform("query", {"selector": "#missing"}) == {
        "selector": "#missing",
        "count": 0,
        "text": None,
    }
    assert backend.perform("evaluate", {"script": "() => 7"}) == {"value": 7}
    shot = backend.perform("screenshot", {"path": "shots/a.png"})
    assert Path(shot["path"]).relative_to(tmp_path.resolve()) == Path("shots/a.png")
    assert (
        Path(page.screenshot_calls[-1]["path"]).relative_to(tmp_path.resolve())
        == Path("shots/a.png")
    )

    with pytest.raises(runtime.BrowserRuntimeError, match="evidence"):
        backend.perform("screenshot", {"path": "../escape.png"})


def test_chromium_factory_launches_fresh_headless_browser_each_call():
    runtime = _runtime()
    starter = _Starter()
    factory = runtime.ChromiumBackendFactory(
        fixture_base_url="http://127.0.0.1:43123",
        playwright_start=starter,
        executable_path=r"C:\chrome\chrome.exe",
    )

    first = factory()
    second = factory()
    assert len(starter.instances) == 2
    for instance in starter.instances:
        assert instance.chromium.launch_calls == [
            {"headless": True, "executable_path": r"C:\chrome\chrome.exe"}
        ]
    first.perform("close", {})
    second.perform("close", {})
    assert all(instance.stopped for instance in starter.instances)


def test_obscura_factory_uses_connect_over_cdp_and_reaps_server_process():
    runtime = _runtime()
    starter = _Starter()
    process = _Process()
    captured = {}

    def popen_factory(argv, **kwargs):
        captured["argv"] = list(argv)
        captured["kwargs"] = dict(kwargs)
        return process

    factory = runtime.ObscuraBackendFactory(
        obscura_executable=r"C:\obscura\obscura.exe",
        fixture_base_url="http://127.0.0.1:43123",
        playwright_start=starter,
        popen_factory=popen_factory,
        port_factory=lambda: 43190,
        connect_attempts=1,
    )
    backend = factory()
    assert starter.instances[0].chromium.connect_calls == [
        ("ws://127.0.0.1:43190", {"timeout": 1000})
    ]
    assert captured["argv"][-1] == "--allow-private-network"
    assert captured["kwargs"]["shell"] is False

    backend.perform("close", {})
    assert process.terminated is True
    assert starter.instances[0].stopped is True
