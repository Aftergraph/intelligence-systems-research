from __future__ import annotations

from importlib import import_module
import json
from pathlib import Path

import pytest


def _worker():
    return import_module("experiments.runtime_acceleration.hermes_host_worker")


def test_runtime_flags_are_exact_and_do_not_inherit_cross_condition_state():
    worker = _worker()
    assert worker.runtime_flags("stock") == {
        "TOOLRUSH_FASTLANE": "0",
        "TOOLRUSH_SEARCH": "0",
        "TOOLRUSH_PERSIST": "0",
    }
    assert worker.runtime_flags("toolrush") == {
        "TOOLRUSH_FASTLANE": "1",
        "TOOLRUSH_SEARCH": "1",
        "TOOLRUSH_PERSIST": "1",
    }
    with pytest.raises(ValueError, match="mode"):
        worker.runtime_flags("hybrid")


def test_workspace_path_resolves_relative_fixture_and_rejects_escape(tmp_path: Path):
    worker = _worker()
    workspace = tmp_path / "workspace"
    (workspace / "fixture").mkdir(parents=True)
    source = workspace / "fixture" / "source_a.py"
    source.write_text("deterministic-marker\n", encoding="utf-8")

    assert worker.resolve_workspace_path(workspace, "fixture/source_a.py") == source.resolve()
    with pytest.raises(ValueError, match="workspace"):
        worker.resolve_workspace_path(workspace, "../outside.txt")
    with pytest.raises(ValueError, match="workspace"):
        worker.resolve_workspace_path(workspace, str(tmp_path / "outside.txt"))


def test_read_payload_maps_line_range_to_real_hermes_read_signature(tmp_path: Path):
    worker = _worker()
    workspace = tmp_path / "workspace"
    (workspace / "fixture").mkdir(parents=True)
    target = workspace / "fixture" / "source_a.py"
    target.write_text("x\n" * 50, encoding="utf-8")

    kwargs = worker.read_kwargs(
        {"path": "fixture/source_a.py", "start_line": 3, "end_line": 9},
        workspace,
        task_id="r-1",
    )
    assert kwargs == {
        "path": str(target.resolve()),
        "offset": 3,
        "limit": 7,
        "task_id": "r-1",
    }

    with pytest.raises(ValueError, match="line"):
        worker.read_kwargs(
            {"path": "fixture/source_a.py", "start_line": 9, "end_line": 3},
            workspace,
            task_id="bad",
        )


def test_search_payload_maps_query_and_workspace_path(tmp_path: Path):
    worker = _worker()
    workspace = tmp_path / "workspace"
    fixture = workspace / "fixture"
    fixture.mkdir(parents=True)

    kwargs = worker.search_kwargs(
        {"query": "deterministic-marker", "path": "fixture", "limit": 17},
        workspace,
        task_id="s-1",
    )
    assert kwargs == {
        "pattern": "deterministic-marker",
        "path": str(fixture.resolve()),
        "limit": 17,
        "task_id": "s-1",
    }


def test_decode_tool_envelope_ignores_trailing_whitespace_but_not_garbage():
    worker = _worker()
    assert worker.decode_tool_envelope('{"content":"alpha"}\n') == {"content": "alpha"}
    with pytest.raises(ValueError, match="trailing"):
        worker.decode_tool_envelope('{"content":"alpha"}not-json')
    with pytest.raises(TypeError, match="mapping"):
        worker.decode_tool_envelope('[1,2,3]')


class _FileTools:
    def __init__(self):
        self.read_calls = []
        self.search_calls = []

    def read_file_tool(self, **kwargs):
        self.read_calls.append(dict(kwargs))
        return json.dumps({"content": "alpha", "path": kwargs["path"]})

    def search_tool(self, **kwargs):
        self.search_calls.append(dict(kwargs))
        return json.dumps({"matches": [{"line": 1, "text": "deterministic-marker"}]})


class _Env:
    def __init__(self):
        self.calls = []

    def execute(self, command, cwd="", **kwargs):
        self.calls.append((command, cwd, dict(kwargs)))
        return {"output": "trace-ok\n", "returncode": 0, "cwd": cwd}


def test_dispatch_operation_calls_real_style_file_and_shell_surfaces(tmp_path: Path):
    worker = _worker()
    workspace = tmp_path / "workspace"
    fixture = workspace / "fixture"
    fixture.mkdir(parents=True)
    (fixture / "source_a.py").write_text("deterministic-marker\n", encoding="utf-8")
    ft = _FileTools()
    env = _Env()

    read = worker.dispatch_operation(
        "read",
        {"path": "fixture/source_a.py", "start_line": 1, "end_line": 40},
        workspace=workspace,
        file_tools=ft,
        environment=env,
        task_id="r",
    )
    search = worker.dispatch_operation(
        "search",
        {"query": "deterministic-marker", "path": "fixture"},
        workspace=workspace,
        file_tools=ft,
        environment=env,
        task_id="s",
    )
    shell = worker.dispatch_operation(
        "shell",
        {"command": "python -c \"print('trace-ok')\""},
        workspace=workspace,
        file_tools=ft,
        environment=env,
        task_id="t",
    )

    assert read["content"] == "alpha"
    assert search["matches"][0]["text"] == "deterministic-marker"
    assert shell == {"output": "trace-ok\n", "returncode": 0}
    assert env.calls == [("python -c \"print('trace-ok')\"", str(workspace.resolve()), {"bounded_capture": False})]

    with pytest.raises(ValueError, match="unsupported"):
        worker.dispatch_operation(
            "delete_everything",
            {},
            workspace=workspace,
            file_tools=ft,
            environment=env,
            task_id="nope",
        )
