from __future__ import annotations

from importlib import import_module
from pathlib import Path


def _executor():
    return import_module("experiments.runtime_acceleration.phase1_executor").execute_phase1_plan


def _protocol() -> dict:
    return {
        "experiment_id": "JAR-EXP-0013",
        "revision": 3,
        "conditions": {
            "A": {"tool_layer": "stock_hermes", "browser_layer": "chromium"},
            "B": {"tool_layer": "toolrush", "browser_layer": "chromium"},
            "C": {"tool_layer": "stock_hermes", "browser_layer": "obscura"},
            "D": {"tool_layer": "toolrush", "browser_layer": "obscura"},
        },
        "preflight": {
            "cpu_percent_max": 20.0,
            "memory_percent_max": 80.0,
            "require_ac_power": True,
        },
    }


def _plan() -> dict:
    pair_id = "jar-exp-0013-trace-001-pair-001"
    return {
        "experiment_id": "JAR-EXP-0013",
        "phase": "TRACE_REPLAY",
        "plan_only": True,
        "performance_evidence": False,
        "repetitions": 1,
        "conditions": ["A", "B", "C", "D"],
        "trace": {
            "trace_id": "jar-exp-0013-trace-001",
            "revision": 1,
            "steps": [{"operation": "read", "payload": {"path": "fixture/source_a.py"}}],
        },
        "runs": [
            {
                "sequence": index,
                "pair_id": pair_id,
                "condition": condition,
                "trace_id": "jar-exp-0013-trace-001",
                "trace_revision": 1,
            }
            for index, condition in enumerate(("A", "B", "C", "D"), start=1)
        ],
    }


def _probe() -> dict:
    return {
        "experiment_id": "JAR-EXP-0013",
        "state": "READY",
        "pins": {"toolrush": "toolrush-pin", "obscura": "obscura-pin"},
    }


def _snapshot() -> dict:
    return {"cpu_percent": 2.0, "memory_percent": 20.0, "on_ac_power": True}


class _Adapter:
    def __init__(self, condition: str, *, execute_error: bool = False, close_error: bool = False):
        self.condition = condition
        self.execute_error = execute_error
        self.close_error = close_error
        self.close_calls = 0

    def execute(self, operation: str, payload: dict) -> dict:
        if self.execute_error:
            raise RuntimeError(f"execute-failed-{self.condition}")
        return {"operation": operation, "payload": dict(payload)}

    def close(self):
        self.close_calls += 1
        if self.close_error:
            raise RuntimeError(f"close-failed-{self.condition}")
        return {"state": "closed"}


def test_every_constructed_adapter_is_closed_exactly_once_after_its_run(tmp_path: Path):
    adapters: list[_Adapter] = []

    def factory(condition: str):
        adapter = _Adapter(condition, execute_error=condition == "B")
        adapters.append(adapter)
        return adapter

    result = _executor()(
        _plan(),
        _protocol(),
        _probe(),
        evidence_root=tmp_path,
        execution_id="phase1-lifecycle",
        adapter_factory=factory,
        snapshot_provider=_snapshot,
    )

    assert [adapter.condition for adapter in adapters] == ["A", "B", "C", "D"]
    assert [adapter.close_calls for adapter in adapters] == [1, 1, 1, 1]
    assert result["completed_runs"] == 4
    b_run = next(run for run in result["runs"] if run["condition"] == "B")
    assert b_run["verifier"]["classification"] == "EXECUTION_ERROR"


def test_cleanup_failure_invalidates_the_run_instead_of_preserving_timings(tmp_path: Path):
    adapters: list[_Adapter] = []

    def factory(condition: str):
        adapter = _Adapter(condition, close_error=condition == "C")
        adapters.append(adapter)
        return adapter

    result = _executor()(
        _plan(),
        _protocol(),
        _probe(),
        evidence_root=tmp_path,
        execution_id="phase1-cleanup-failure",
        adapter_factory=factory,
        snapshot_provider=_snapshot,
    )

    c_run = next(run for run in result["runs"] if run["condition"] == "C")
    assert c_run["verifier"]["verified"] is False
    assert c_run["verifier"]["classification"] == "EXECUTION_ERROR"
    assert c_run["metrics"]["trace_wall_clock_ms"] is None
    assert c_run["metrics"]["tool_time_total_ms"] is None
    assert c_run["metrics"]["browser_time_total_ms"] is None
    assert result["correctness_failures"] == 1
    assert all(adapter.close_calls == 1 for adapter in adapters)
