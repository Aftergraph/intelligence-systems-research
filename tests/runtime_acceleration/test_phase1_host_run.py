from __future__ import annotations

from contextlib import contextmanager
from importlib import import_module
from pathlib import Path

import pytest


def _module():
    return import_module("experiments.runtime_acceleration.phase1_host_run")


def _config() -> dict:
    return {
        "experiment_id": "JAR-EXP-0013",
        "hermes_python": r"C:\hermes\.venv\Scripts\python.exe",
        "hermes_root": r"C:\hermes",
        "workspace": r"C:\Aftergraph\JAR-EXP-0013\workspace",
        "toolrush_plugin": r"C:\hermes\plugins\toolrush\__init__.py",
        "obscura_executable": r"C:\obscura\obscura.exe",
        "chromium_executable": r"C:\chromium\chrome.exe",
    }


def _protocol() -> dict:
    return {
        "experiment_id": "JAR-EXP-0013",
        "revision": 3,
        "pins": {
            "toolrush": "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e",
            "obscura": "a1e09de68c7617b8079fbb1661b0548c501971c1",
        },
    }


def _probe(state: str = "READY") -> dict:
    return {
        "experiment_id": "JAR-EXP-0013",
        "state": state,
        "pins": dict(_protocol()["pins"]),
    }


def _plan() -> dict:
    return {
        "experiment_id": "JAR-EXP-0013",
        "phase": "TRACE_REPLAY",
        "plan_only": True,
        "conditions": ["A", "B", "C", "D"],
        "runs": [],
    }


class _Worker:
    def __init__(self, mode: str):
        self.mode = mode
        self.close_calls = 0

    def handlers(self):
        return {
            "read": lambda payload: {"mode": self.mode, "payload": payload},
            "search": lambda payload: {"mode": self.mode, "payload": payload},
            "shell": lambda payload: {"mode": self.mode, "payload": payload},
        }

    def close(self):
        self.close_calls += 1


class _BrowserFactory:
    created: list[dict] = []

    def __init__(self, **kwargs):
        self.kwargs = dict(kwargs)
        type(self).created.append(self.kwargs)

    def __call__(self):
        raise AssertionError("browser factory must stay lazy until executor asks for a condition")


@contextmanager
def _fixture_context(calls: list[str]):
    calls.append("fixture-enter")
    try:
        yield "http://127.0.0.1:43123"
    finally:
        calls.append("fixture-exit")


def test_non_ready_probe_blocks_before_any_runtime_is_started(tmp_path: Path):
    module = _module()
    calls: list[str] = []

    with pytest.raises(module.Phase1HostRunError, match="READY"):
        module.run_phase1_host(
            _config(),
            _plan(),
            _protocol(),
            _probe("CONTAMINATED"),
            evidence_root=tmp_path,
            execution_id="blocked",
            fixture_server_factory=lambda: _fixture_context(calls),
            worker_factory=lambda config, mode: (_ for _ in ()).throw(
                AssertionError("worker must not start")
            ),
            executor=lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("executor must not run")
            ),
        )

    assert calls == []


def test_ready_host_composes_exact_runtime_and_closes_both_workers(tmp_path: Path):
    module = _module()
    calls: list[str] = []
    workers: list[_Worker] = []
    adapter_build = {}
    executor_call = {}
    _BrowserFactory.created.clear()

    def worker_factory(config, mode):
        calls.append(f"worker:{mode}")
        worker = _Worker(mode)
        workers.append(worker)
        return worker

    def adapter_builder(**kwargs):
        adapter_build.update(kwargs)
        return lambda condition: {"condition": condition}

    def executor(plan, protocol, probe, **kwargs):
        executor_call.update(kwargs)
        return {
            "experiment_id": "JAR-EXP-0013",
            "phase": "TRACE_REPLAY",
            "state": "COMPLETE",
        }

    result = module.run_phase1_host(
        _config(),
        _plan(),
        _protocol(),
        _probe(),
        evidence_root=tmp_path,
        execution_id="phase1-real",
        fixture_server_factory=lambda: _fixture_context(calls),
        worker_factory=worker_factory,
        chromium_factory_cls=_BrowserFactory,
        obscura_factory_cls=_BrowserFactory,
        adapter_factory_builder=adapter_builder,
        executor=executor,
        snapshot_provider=lambda: {"cpu_percent": 1.0},
    )

    assert result["state"] == "COMPLETE"
    assert calls == ["fixture-enter", "worker:stock", "worker:toolrush", "fixture-exit"]
    assert [worker.close_calls for worker in workers] == [1, 1]
    assert len(_BrowserFactory.created) == 2
    assert all(
        item["fixture_base_url"] == "http://127.0.0.1:43123"
        for item in _BrowserFactory.created
    )
    assert _BrowserFactory.created[0]["executable_path"] == _config()["chromium_executable"]
    assert _BrowserFactory.created[1]["obscura_executable"] == _config()["obscura_executable"]
    assert adapter_build["stock_worker"] is workers[0]
    assert adapter_build["toolrush_worker"] is workers[1]
    assert adapter_build["toolrush_revision"] == _protocol()["pins"]["toolrush"]
    assert adapter_build["obscura_revision"] == _protocol()["pins"]["obscura"]
    assert executor_call["execution_id"] == "phase1-real"
    assert executor_call["evidence_root"] == tmp_path
    assert callable(executor_call["adapter_factory"])
    assert callable(executor_call["snapshot_provider"])


def test_pin_drift_blocks_before_fixture_or_workers(tmp_path: Path):
    module = _module()
    calls: list[str] = []
    probe = _probe()
    probe["pins"]["toolrush"] = "0" * 40

    with pytest.raises(module.Phase1HostRunError, match="pin"):
        module.run_phase1_host(
            _config(),
            _plan(),
            _protocol(),
            probe,
            evidence_root=tmp_path,
            execution_id="pin-drift",
            fixture_server_factory=lambda: _fixture_context(calls),
            worker_factory=lambda config, mode: (_ for _ in ()).throw(
                AssertionError("worker must not start")
            ),
        )

    assert calls == []


def test_executor_failure_still_closes_both_workers_and_fixture(tmp_path: Path):
    module = _module()
    calls: list[str] = []
    workers: list[_Worker] = []
    _BrowserFactory.created.clear()

    def worker_factory(config, mode):
        worker = _Worker(mode)
        workers.append(worker)
        return worker

    with pytest.raises(RuntimeError, match="executor-boom"):
        module.run_phase1_host(
            _config(),
            _plan(),
            _protocol(),
            _probe(),
            evidence_root=tmp_path,
            execution_id="executor-error",
            fixture_server_factory=lambda: _fixture_context(calls),
            worker_factory=worker_factory,
            chromium_factory_cls=_BrowserFactory,
            obscura_factory_cls=_BrowserFactory,
            adapter_factory_builder=lambda **kwargs: (lambda condition: condition),
            executor=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("executor-boom")),
        )

    assert [worker.close_calls for worker in workers] == [1, 1]
    assert calls == ["fixture-enter", "fixture-exit"]
