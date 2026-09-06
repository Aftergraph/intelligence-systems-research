from __future__ import annotations

from importlib import import_module
import json
from pathlib import Path

import pytest


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


def _plan(order=("B", "D", "A", "C")) -> dict:
    pair_id = "jar-exp-0013-trace-001-pair-001"
    return {
        "experiment_id": "JAR-EXP-0013",
        "phase": "TRACE_REPLAY",
        "plan_only": True,
        "performance_evidence": False,
        "seed": 130013,
        "repetitions": 1,
        "conditions": ["A", "B", "C", "D"],
        "trace": {
            "trace_id": "jar-exp-0013-trace-001",
            "revision": 1,
            "steps": [
                {"operation": "read", "payload": {"path": "fixture/source_a.py"}},
                {"operation": "browser_query", "payload": {"selector": "#deterministic-marker"}},
            ],
        },
        "runs": [
            {
                "sequence": index,
                "pair_id": pair_id,
                "condition": condition,
                "trace_id": "jar-exp-0013-trace-001",
                "trace_revision": 1,
            }
            for index, condition in enumerate(order, start=1)
        ],
    }


def _ready_probe() -> dict:
    return {
        "experiment_id": "JAR-EXP-0013",
        "state": "READY",
        "pins": {"toolrush": "toolrush-pin", "obscura": "obscura-pin"},
    }


class _Adapter:
    def __init__(self, condition: str, *, mismatch: bool = False):
        self.condition = condition
        self.mismatch = mismatch

    def execute(self, operation: str, payload: dict) -> dict:
        observable = {"operation": operation, "payload": dict(payload)}
        if self.mismatch and operation == "browser_query":
            observable["result"] = "DIFFERENT"
        return observable


def _clean_snapshot() -> dict:
    return {"cpu_percent": 3.0, "memory_percent": 21.0, "on_ac_power": True}


def test_clean_pair_executes_frozen_order_and_writes_append_only_evidence(tmp_path: Path):
    calls: list[str] = []

    def factory(condition: str):
        calls.append(condition)
        return _Adapter(condition)

    result = _executor()(
        _plan(),
        _protocol(),
        _ready_probe(),
        evidence_root=tmp_path,
        execution_id="phase1-clean",
        adapter_factory=factory,
        snapshot_provider=_clean_snapshot,
    )

    assert calls == ["B", "D", "A", "C"]
    assert result["state"] == "COMPLETE"
    assert result["clean_pairs"] == 1
    assert result["contaminated_pairs"] == 0
    assert result["completed_runs"] == 4
    assert result["correctness_failures"] == 0

    session = tmp_path / "phase1-clean"
    summary = json.loads((session / "summary.json").read_text(encoding="utf-8"))
    assert summary["completed_runs"] == 4
    run_dirs = sorted((session / "runs").iterdir())
    assert len(run_dirs) == 4
    assert all((path / "artifacts.sha256").exists() for path in run_dirs)


def test_contaminated_block_is_recorded_and_never_executes_treatments(tmp_path: Path):
    def forbidden_factory(condition: str):
        raise AssertionError(f"treatment {condition} must not execute on a contaminated block")

    result = _executor()(
        _plan(("A", "B", "C", "D")),
        _protocol(),
        _ready_probe(),
        evidence_root=tmp_path,
        execution_id="phase1-contaminated",
        adapter_factory=forbidden_factory,
        snapshot_provider=lambda: {
            "cpu_percent": 91.0,
            "memory_percent": 25.0,
            "on_ac_power": True,
        },
    )

    assert result["state"] == "COMPLETE_WITH_EXCLUSIONS"
    assert result["clean_pairs"] == 0
    assert result["contaminated_pairs"] == 1
    assert result["completed_runs"] == 0
    assert result["excluded_pair_ids"] == ["jar-exp-0013-trace-001-pair-001"]

    block = json.loads(
        (
            tmp_path
            / "phase1-contaminated"
            / "blocks"
            / "jar-exp-0013-trace-001-pair-001.json"
        ).read_text(encoding="utf-8")
    )
    assert block["state"] == "CONTAMINATED"
    assert block["preflight"]["reasons"] == ["cpu_percent"]


def test_semantic_mismatch_is_preserved_as_correctness_failure(tmp_path: Path):
    def factory(condition: str):
        return _Adapter(condition, mismatch=condition == "B")

    result = _executor()(
        _plan(("A", "B", "C", "D")),
        _protocol(),
        _ready_probe(),
        evidence_root=tmp_path,
        execution_id="phase1-mismatch",
        adapter_factory=factory,
        snapshot_provider=_clean_snapshot,
    )

    assert result["state"] == "COMPLETE_WITH_CORRECTNESS_FAILURES"
    assert result["correctness_failures"] == 1
    b_run = next(run for run in result["runs"] if run["condition"] == "B")
    assert b_run["verifier"]["verified"] is False
    assert b_run["verifier"]["classification"] == "SEMANTIC_MISMATCH"


def test_execution_id_is_immutable_and_second_attempt_fails_before_adapter_use(tmp_path: Path):
    calls: list[str] = []

    def factory(condition: str):
        calls.append(condition)
        return _Adapter(condition)

    execute = _executor()
    kwargs = dict(
        evidence_root=tmp_path,
        execution_id="phase1-immutable",
        adapter_factory=factory,
        snapshot_provider=_clean_snapshot,
    )
    execute(_plan(), _protocol(), _ready_probe(), **kwargs)
    first_call_count = len(calls)

    with pytest.raises(FileExistsError):
        execute(_plan(), _protocol(), _ready_probe(), **kwargs)

    assert len(calls) == first_call_count


def test_executor_refuses_non_ready_host_before_creating_evidence(tmp_path: Path):
    probe = _ready_probe()
    probe["state"] = "CONTAMINATED"

    with pytest.raises(ValueError, match="READY"):
        _executor()(
            _plan(),
            _protocol(),
            probe,
            evidence_root=tmp_path,
            execution_id="phase1-blocked",
            adapter_factory=lambda condition: _Adapter(condition),
            snapshot_provider=_clean_snapshot,
        )

    assert not (tmp_path / "phase1-blocked").exists()
