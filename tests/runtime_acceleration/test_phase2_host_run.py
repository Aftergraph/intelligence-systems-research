from pathlib import Path

import pytest

from experiments.runtime_acceleration.phase2_host_run import (
    Phase2WorkerLifecycle,
    run_controlled_phase2,
    validate_phase2_worker_surfaces,
)
from experiments.runtime_acceleration.phase2_tool_microbench import build_tool_microbench_plan


TOOLRUSH_PIN = "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e"


def _protocol():
    return {
        "experiment_id": "JAR-EXP-0013",
        "revision": 3,
        "conditions": {
            "A": {"tool_layer": "stock_hermes"},
            "B": {"tool_layer": "toolrush"},
        },
        "pins": {"toolrush": TOOLRUSH_PIN},
        "preflight": {
            "cpu_percent_max": 20.0,
            "memory_percent_max": 80.0,
            "require_ac_power": True,
        },
        "confirmatory": {
            "minimum_microbenchmark_warm_repetitions": 2,
            "run_order": "randomized_within_paired_blocks",
        },
        "analysis": {"bootstrap_seed": 130013},
    }


def _plan():
    return build_tool_microbench_plan(
        {
            "workload_id": "phase2-host-test",
            "warm_repetitions": 2,
            "operations": ["bounded_read", "exact_search"],
        },
        _protocol(),
    )


def _probe():
    return {
        "experiment_id": "JAR-EXP-0013",
        "state": "READY",
        "pins": {"toolrush": TOOLRUSH_PIN},
    }


def _snapshot():
    return {"cpu_percent": 1.0, "memory_percent": 25.0, "on_ac_power": True}


class FakeWorker:
    def __init__(self, mode, events, workspace):
        self.mode = mode
        self.events = events
        self.closed = 0
        self.surface = {
            "mode": mode,
            "rpc": {
                "transport": "tcp_loopback",
                "sequential_available": True,
                "parallel_available": mode == "toolrush",
            },
        }
        fixture = Path(workspace) / "fixture" / "source_a.py"
        assert fixture.is_file(), "fixture must exist before workers start"
        self.events.append(f"start:{mode}")

    def execute(self, operation, payload):
        self.events.append(f"execute:{self.mode}:{operation}")
        if operation == "rpc_batch":
            return {
                "results": [
                    {"tool": call["tool"], "args": call["args"]}
                    for call in payload["calls"]
                ]
            }
        return {"operation": operation, "payload": payload}

    def close(self):
        self.closed += 1
        self.events.append(f"close:{self.mode}")


def _worker_factory(events, workers):
    def factory(config, mode):
        worker = FakeWorker(mode, events, config["workspace"])
        workers.append(worker)
        return worker

    return factory


def test_surface_validation_requires_stock_sequential_and_toolrush_parallel():
    events = []
    stock = FakeWorker("stock", events, ".") if (Path("fixture") / "source_a.py").is_file() else None
    if stock is None:
        class SurfaceOnly:
            def __init__(self, mode, sequential=True, parallel=False):
                self.mode = mode
                self.surface = {
                    "mode": mode,
                    "rpc": {
                        "transport": "tcp_loopback",
                        "sequential_available": sequential,
                        "parallel_available": parallel,
                    },
                }

        stock = SurfaceOnly("stock", sequential=True, parallel=False)
        toolrush = SurfaceOnly("toolrush", sequential=True, parallel=True)
    else:
        toolrush = stock
        toolrush.mode = "toolrush"
        toolrush.surface["mode"] = "toolrush"
        toolrush.surface["rpc"]["parallel_available"] = True

    validate_phase2_worker_surfaces(stock, toolrush)

    toolrush.surface["rpc"]["parallel_available"] = False
    with pytest.raises(RuntimeError, match="parallel"):
        validate_phase2_worker_surfaces(stock, toolrush)


def test_worker_lifecycle_rotates_once_per_operation_and_closes_exactly_once(tmp_path: Path):
    events = []
    workers = []
    config = {"experiment_id": "JAR-EXP-0013", "workspace": str(tmp_path / "workspace")}
    from experiments.runtime_acceleration.phase2_bindings import prepare_tool_microbench_workspace

    prepare_tool_microbench_workspace(config["workspace"])
    lifecycle = Phase2WorkerLifecycle(
        config,
        worker_factory=_worker_factory(events, workers),
    )
    try:
        pair_one = [
            {"operation": "bounded_read", "condition": "A"},
            {"operation": "bounded_read", "condition": "B"},
        ]
        pair_two = [
            {"operation": "exact_search", "condition": "A"},
            {"operation": "exact_search", "condition": "B"},
        ]
        lifecycle.prepare_pair("bounded-read-cold", pair_one)
        first_workers = list(workers)
        lifecycle.prepare_pair("bounded-read-warm", pair_one)
        assert workers == first_workers
        lifecycle.prepare_pair("exact-search-cold", pair_two)
        assert len(workers) == 4
        assert all(worker.closed == 1 for worker in first_workers)
    finally:
        lifecycle.close()
    assert all(worker.closed == 1 for worker in workers)


def test_controlled_host_starts_fresh_pair_before_first_preflight_of_each_operation(tmp_path: Path):
    events = []
    workers = []
    config = {"experiment_id": "JAR-EXP-0013", "workspace": str(tmp_path / "workspace")}

    def snapshot_provider():
        events.append("snapshot")
        return _snapshot()

    summary = run_controlled_phase2(
        config,
        _plan(),
        _probe(),
        _protocol(),
        evidence_root=tmp_path / "evidence",
        execution_id="phase2-host-test",
        worker_factory=_worker_factory(events, workers),
        snapshot_provider=snapshot_provider,
    )

    assert summary["state"] == "COMPLETE"
    assert summary["planned_pairs"] == 6
    assert summary["completed_runs"] == 12
    assert len(workers) == 4
    assert all(worker.closed == 1 for worker in workers)

    starts = [index for index, event in enumerate(events) if event.startswith("start:")]
    snapshots = [index for index, event in enumerate(events) if event == "snapshot"]
    assert len(starts) == 4
    assert len(snapshots) == 6
    assert starts[0] < snapshots[0] and starts[1] < snapshots[0]
    assert starts[2] < snapshots[3] and starts[3] < snapshots[3]


def test_controlled_host_closes_workers_when_executor_raises(tmp_path: Path):
    events = []
    workers = []
    config = {"experiment_id": "JAR-EXP-0013", "workspace": str(tmp_path / "workspace")}

    def exploding_snapshot():
        raise RuntimeError("snapshot exploded")

    with pytest.raises(RuntimeError, match="snapshot exploded"):
        run_controlled_phase2(
            config,
            _plan(),
            _probe(),
            _protocol(),
            evidence_root=tmp_path / "evidence",
            execution_id="phase2-host-explode",
            worker_factory=_worker_factory(events, workers),
            snapshot_provider=exploding_snapshot,
        )
    assert workers
    assert all(worker.closed == 1 for worker in workers)
