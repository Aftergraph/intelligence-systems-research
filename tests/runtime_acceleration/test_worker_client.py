from __future__ import annotations

import io
import json
from importlib import import_module

import pytest


def _bridge():
    return import_module("experiments.runtime_acceleration.runtime_bridge")


def _surface(mode: str) -> dict:
    flags = "1" if mode == "toolrush" else "0"
    return {
        "mode": mode,
        "symbols": {
            "tools.file_tools.read_file_tool": {"status": "READY"},
            "tools.file_tools.search_tool": {"status": "READY"},
            "tools.environments.local.LocalEnvironment": {"status": "READY"},
            "tools.file_operations.ShellFileOperations": {"status": "READY"},
        },
        "toolrush_plugin_loaded": mode == "toolrush",
        "toolrush_flags": {
            "TOOLRUSH_FASTLANE": flags,
            "TOOLRUSH_SEARCH": flags,
            "TOOLRUSH_PERSIST": flags,
        },
    }


class _FakeProcess:
    def __init__(self, stdout_lines: list[dict], *, stderr_text: str = ""):
        self.stdin = io.StringIO()
        self.stdout = io.StringIO("".join(json.dumps(item) + "\n" for item in stdout_lines))
        self.stderr = io.StringIO(stderr_text)
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


def _config() -> dict:
    return {
        "hermes_python": r"C:\hermes\.venv\Scripts\python.exe",
        "hermes_root": r"C:\hermes",
        "workspace": r"C:\Aftergraph\JAR-EXP-0013\workspace",
        "toolrush_plugin": r"C:\hermes\plugins\toolrush\__init__.py",
    }


def test_client_validates_handshake_sends_requests_and_exposes_equal_handlers(tmp_path):
    bridge = _bridge()
    process = _FakeProcess(
        [
            {"type": "ready", "surface": _surface("stock")},
            {"id": "req-1", "ok": True, "result": {"content": "alpha"}},
            {"type": "closed"},
        ]
    )
    captured = {}

    def popen_factory(argv, **kwargs):
        captured["argv"] = list(argv)
        captured["kwargs"] = dict(kwargs)
        return process

    client = bridge.HermesWorkerClient(
        _config(),
        "stock",
        popen_factory=popen_factory,
        id_factory=lambda: "req-1",
        startup_timeout_s=1,
        request_timeout_s=1,
        repo_root=tmp_path,
    )

    assert client.surface["mode"] == "stock"
    assert set(client.handlers()) == {"read", "search", "shell"}
    assert client.execute("read", {"path": "fixture/source_a.py"}) == {"content": "alpha"}
    sent = json.loads(process.stdin.getvalue().splitlines()[0])
    assert sent == {
        "id": "req-1",
        "operation": "read",
        "payload": {"path": "fixture/source_a.py"},
    }
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["cwd"] == str(tmp_path.resolve())
    client.close()
    sent_lines = [json.loads(line) for line in process.stdin.getvalue().splitlines()]
    assert sent_lines[-1] == {"type": "close"}
    assert process.returncode == 0
    assert process.terminated is False
    assert process.killed is False


def test_client_treatment_argv_and_surface_are_toolrush_specific(tmp_path):
    bridge = _bridge()
    process = _FakeProcess([
        {"type": "ready", "surface": _surface("toolrush")},
        {"type": "closed"},
    ])
    captured = {}

    def popen_factory(argv, **kwargs):
        captured["argv"] = list(argv)
        return process

    client = bridge.HermesWorkerClient(
        _config(),
        "toolrush",
        popen_factory=popen_factory,
        startup_timeout_s=1,
        repo_root=tmp_path,
    )
    assert "--toolrush-plugin" in captured["argv"]
    assert client.surface["toolrush_plugin_loaded"] is True
    client.close()


def test_client_surfaces_worker_errors_without_fallback(tmp_path):
    bridge = _bridge()
    process = _FakeProcess(
        [
            {"type": "ready", "surface": _surface("stock")},
            {
                "id": "req-error",
                "ok": False,
                "error": {"type": "ValueError", "message": "bad path"},
            },
            {"type": "closed"},
        ]
    )
    client = bridge.HermesWorkerClient(
        _config(),
        "stock",
        popen_factory=lambda argv, **kwargs: process,
        id_factory=lambda: "req-error",
        startup_timeout_s=1,
        request_timeout_s=1,
        repo_root=tmp_path,
    )
    with pytest.raises(bridge.RuntimeBridgeError, match="ValueError.*bad path"):
        client.execute("read", {"path": "../escape"})
    client.close()


def test_client_rejects_invalid_ready_surface(tmp_path):
    bridge = _bridge()
    bad = _surface("stock")
    bad["toolrush_flags"]["TOOLRUSH_SEARCH"] = "1"
    process = _FakeProcess([{"type": "ready", "surface": bad}])
    with pytest.raises(bridge.RuntimeBridgeError, match="TOOLRUSH_SEARCH"):
        bridge.HermesWorkerClient(
            _config(),
            "stock",
            popen_factory=lambda argv, **kwargs: process,
            startup_timeout_s=1,
            repo_root=tmp_path,
        )
