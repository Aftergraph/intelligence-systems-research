from pathlib import Path

import pytest

from experiments.runtime_acceleration.phase2_tool_microbench import (
    build_tool_microbench_plan,
    execute_tool_microbench_plan,
    write_tool_microbench_plan,
)


def _protocol(*, minimum_warm=2):
    return {
        "experiment_id": "JAR-EXP-0013",
        "revision": 3,
        "conditions": {
            "A": {"tool_layer": "stock_hermes"},
            "B": {"tool_layer": "toolrush"},
            "C": {"tool_layer": "stock_hermes"},
            "D": {"tool_layer": "toolrush"},
        },
        "pins": {"toolrush": "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e"},
        "preflight": {
            "cpu_percent_max": 20.0,
            "memory_percent_max": 80.0,
            "require_ac_power": True,
        },
        "confirmatory": {
            "minimum_microbenchmark_warm_repetitions": minimum_warm,
            "run_order": "randomized_within_paired_blocks",
        },
        "analysis": {"bootstrap_seed": 130013},
    }


def _workload(*, warm=2):
    return {
        "workload_id": "jar-exp-0013-tool-microbench-v1",
        "warm_repetitions": warm,
        "operations": ["bounded_read", "exact_search"],
    }


def test_plan_is_seeded_paired_and_contains_one_cold_plus_warm_samples():
    plan = build_tool_microbench_plan(_workload(), _protocol())
    again = build_tool_microbench_plan(_workload(), _protocol())

    assert plan == again
    assert plan["experiment_id"] == "JAR-EXP-0013"
    assert plan["phase"] == "TOOL_MICROBENCH"
    assert plan["conditions"] == ["A", "B"]
    assert plan["seed"] == 130013
    assert plan["warm_repetitions"] == 2
    assert plan["plan_only"] is True
    assert plan["performance_evidence"] is False

    assert plan["paired_blocks"] == 6
    assert plan["planned_runs"] == 12
    assert [run["sequence"] for run in plan["runs"]] == list(range(1, 13))

    grouped = {}
    for run in plan["runs"]:
        grouped.setdefault(run["pair_id"], []).append(run)
    assert len(grouped) == 6
    assert all({run["condition"] for run in runs} == {"A", "B"} for runs in grouped.values())
    assert all(len(runs) == 2 for runs in grouped.values())

    for operation in _workload()["operations"]:
        samples = [runs[0] for runs in grouped.values() if runs[0]["operation"] == operation]
        assert sum(sample["sample_kind"] == "cold" for sample in samples) == 1
        assert sorted(
            sample["repetition"] for sample in samples if sample["sample_kind"] == "warm"
        ) == [1, 2]


def test_plan_rejects_underpowered_or_ambiguous_workloads():
    with pytest.raises(ValueError, match="warm repetitions"):
        build_tool_microbench_plan(_workload(warm=1), _protocol(minimum_warm=2))

    duplicate = _workload()
    duplicate["operations"] = ["bounded_read", "bounded_read"]
    with pytest.raises(ValueError, match="unique"):
        build_tool_microbench_plan(duplicate, _protocol())


def test_plan_writer_is_exclusive(tmp_path: Path):
    plan = build_tool_microbench_plan(_workload(), _protocol())
    destination = tmp_path / "phase2-plan.json"
    write_tool_microbench_plan(destination, plan)
    with pytest.raises(FileExistsError):
        write_tool_microbench_plan(destination, plan)


class FakeRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, condition, operation, sample_kind, repetition):
        self.calls.append((condition, operation, sample_kind, repetition))
        return {
            "observable": {"operation": operation, "value": 7},
            "elapsed_ms": 10.0 if condition == "A" else 6.0,
            "stderr": "",
        }


def _clean_snapshot():
    return {
        "cpu_percent": 5.0,
        "memory_percent": 40.0,
        "on_ac_power": True,
    }


def test_executor_preflights_each_pair_preserves_pairing_and_writes_evidence(tmp_path: Path):
    plan = build_tool_microbench_plan(_workload(), _protocol())
    runner = FakeRunner()
    snapshots = []

    def snapshot_provider():
        snapshots.append(1)
        return _clean_snapshot()

    summary = execute_tool_microbench_plan(
        plan,
        _protocol(),
        {
            "experiment_id": "JAR-EXP-0013",
            "state": "READY",
            "pins": {"toolrush": "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e"},
        },
        evidence_root=tmp_path,
        execution_id="phase2-test",
        operation_runner=runner,
        snapshot_provider=snapshot_provider,
    )

    assert summary["state"] == "COMPLETE"
    assert summary["phase"] == "TOOL_MICROBENCH"
    assert summary["planned_pairs"] == 6
    assert summary["clean_pairs"] == 6
    assert summary["completed_runs"] == 12
    assert summary["correctness_failures"] == 0
    assert summary["performance_evidence"] is True
    assert len(snapshots) == 6
    assert len(runner.calls) == 12

    session = tmp_path / "phase2-test"
    assert (session / "summary.json").is_file()
    assert len(list((session / "blocks").glob("*.json"))) == 6
    assert len(list((session / "runs").iterdir())) == 12


def test_executor_records_contaminated_pair_without_running_either_condition(tmp_path: Path):
    plan = build_tool_microbench_plan(_workload(), _protocol())
    runner = FakeRunner()
    calls = 0

    def snapshot_provider():
        nonlocal calls
        calls += 1
        snapshot = _clean_snapshot()
        if calls == 2:
            snapshot["cpu_percent"] = 99.0
        return snapshot

    summary = execute_tool_microbench_plan(
        plan,
        _protocol(),
        {
            "experiment_id": "JAR-EXP-0013",
            "state": "READY",
            "pins": {"toolrush": "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e"},
        },
        evidence_root=tmp_path,
        execution_id="phase2-contaminated",
        operation_runner=runner,
        snapshot_provider=snapshot_provider,
    )

    assert summary["state"] == "COMPLETE_WITH_EXCLUSIONS"
    assert summary["contaminated_pairs"] == 1
    assert summary["completed_runs"] == 10
    assert len(runner.calls) == 10


def test_executor_fails_closed_on_host_or_toolrush_pin_mismatch(tmp_path: Path):
    plan = build_tool_microbench_plan(_workload(), _protocol())
    runner = FakeRunner()

    with pytest.raises(ValueError, match="READY"):
        execute_tool_microbench_plan(
            plan,
            _protocol(),
            {"experiment_id": "JAR-EXP-0013", "state": "BLOCKED", "pins": {}},
            evidence_root=tmp_path,
            execution_id="phase2-blocked",
            operation_runner=runner,
            snapshot_provider=_clean_snapshot,
        )

    with pytest.raises(ValueError, match="ToolRush pin"):
        execute_tool_microbench_plan(
            plan,
            _protocol(),
            {
                "experiment_id": "JAR-EXP-0013",
                "state": "READY",
                "pins": {"toolrush": "wrong"},
            },
            evidence_root=tmp_path,
            execution_id="phase2-pin-mismatch",
            operation_runner=runner,
            snapshot_provider=_clean_snapshot,
        )
