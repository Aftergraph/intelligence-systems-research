import json
from pathlib import Path

import pytest

from experiments.runtime_acceleration.measurement_plan import (
    CONDITIONS,
    build_trace_measurement_plan,
    write_measurement_plan,
)


def _trace():
    return {
        "trace_id": "trace-001",
        "revision": 1,
        "steps": [
            {"operation": "read", "payload": {"path": "fixture/a.txt"}},
            {"operation": "browser_navigate", "payload": {"url": "fixture://static"}},
        ],
    }


def test_trace_plan_is_seeded_paired_and_balanced():
    plan = build_trace_measurement_plan(_trace(), repetitions=20, seed=130013)
    assert plan["experiment_id"] == "JAR-EXP-0013"
    assert plan["phase"] == "TRACE_REPLAY"
    assert plan["plan_only"] is True
    assert plan["seed"] == 130013
    assert len(plan["runs"]) == 80

    by_pair = {}
    for run in plan["runs"]:
        by_pair.setdefault(run["pair_id"], []).append(run)
    assert len(by_pair) == 20
    assert all({run["condition"] for run in runs} == set(CONDITIONS) for runs in by_pair.values())
    assert all(len(runs) == 4 for runs in by_pair.values())

    repeated = build_trace_measurement_plan(_trace(), repetitions=20, seed=130013)
    assert repeated == plan


def test_trace_plan_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        build_trace_measurement_plan({}, repetitions=20, seed=1)
    with pytest.raises(ValueError):
        build_trace_measurement_plan(_trace(), repetitions=0, seed=1)
    with pytest.raises(ValueError):
        build_trace_measurement_plan({"trace_id": "x", "revision": 1, "steps": []}, repetitions=1, seed=1)


def test_measurement_plan_writer_refuses_overwrite(tmp_path: Path):
    output = tmp_path / "plan.json"
    plan = build_trace_measurement_plan(_trace(), repetitions=2, seed=7)
    write_measurement_plan(output, plan)
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded == plan
    with pytest.raises(FileExistsError):
        write_measurement_plan(output, plan)
