from pathlib import Path

import pytest

from experiments.runtime_acceleration.phase2_bindings import (
    FROZEN_TOOL_OPERATIONS,
    ToolMicrobenchOperationRunner,
    build_operation_spec,
    prepare_tool_microbench_workspace,
)


EXPECTED = (
    "bounded_read",
    "paginated_read",
    "exact_search",
    "repository_search",
    "context_search",
    "no_match_search",
    "file_discovery",
    "shell_builtin",
    "python_process",
    "git_process",
    "sequential_read_rpc",
    "parallel_read_rpc",
    "mixed_read_search_rpc",
)


def test_frozen_operations_match_preregistered_workload_exactly():
    assert FROZEN_TOOL_OPERATIONS == EXPECTED
    for operation in EXPECTED:
        spec = build_operation_spec(operation)
        assert spec["operation_name"] == operation
        assert spec["lane"] in {"worker", "rpc"}
    with pytest.raises(ValueError, match="unsupported frozen tool microbenchmark operation"):
        build_operation_spec("invented_fast_path")


def test_worker_specs_use_only_real_hermes_worker_surfaces():
    for operation in EXPECTED[:10]:
        spec = build_operation_spec(operation)
        assert spec["lane"] == "worker"
        assert spec["worker_operation"] in {"read", "search", "shell"}
        assert isinstance(spec["payload"], dict)

    discovery = build_operation_spec("file_discovery")
    assert discovery["worker_operation"] == "search"
    assert discovery["payload"]["target"] == "files"
    assert discovery["payload"]["query"] == "*.py"


def test_rpc_specs_preserve_input_order_and_make_parallelism_condition_explicit():
    sequential = build_operation_spec("sequential_read_rpc")
    parallel = build_operation_spec("parallel_read_rpc")
    mixed = build_operation_spec("mixed_read_search_rpc")

    assert sequential["lane"] == "rpc"
    assert sequential["strategy_by_condition"] == {"A": "sequential", "B": "sequential"}
    assert parallel["strategy_by_condition"] == {"A": "sequential", "B": "parallel"}
    assert mixed["strategy_by_condition"] == {"A": "sequential", "B": "parallel"}
    assert [call["tool"] for call in parallel["calls"]] == ["read_file"] * 4
    assert [call["tool"] for call in mixed["calls"]] == [
        "read_file",
        "search_files",
        "read_file",
        "search_files",
    ]


def test_workspace_fixture_is_deterministic_and_refuses_existing_nonfixture_content(tmp_path: Path):
    workspace = tmp_path / "workspace"
    result = prepare_tool_microbench_workspace(workspace)
    assert result == prepare_tool_microbench_workspace(workspace)
    assert (workspace / "fixture" / "source_a.py").is_file()
    assert (workspace / "fixture" / "source_b.py").is_file()
    assert "deterministic-marker-042" in (workspace / "fixture" / "source_a.py").read_text(encoding="utf-8")
    assert len((workspace / "fixture" / "source_b.py").read_text(encoding="utf-8").splitlines()) >= 240

    hostile = tmp_path / "hostile"
    (hostile / "fixture").mkdir(parents=True)
    (hostile / "fixture" / "source_a.py").write_text("human data\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="refuses to overwrite"):
        prepare_tool_microbench_workspace(hostile)


class Worker:
    def __init__(self, mode):
        self.mode = mode
        self.calls = []

    def execute(self, operation, payload):
        self.calls.append((operation, payload))
        return {"surface": operation, "payload": payload}


class Timer:
    def __init__(self):
        self.value = 0

    def __call__(self):
        self.value += 1_000_000
        return self.value


def test_operation_runner_selects_exact_worker_condition_and_measures_outer_call():
    stock = Worker("stock")
    toolrush = Worker("toolrush")
    rpc_calls = []
    runner = ToolMicrobenchOperationRunner(
        stock_worker=stock,
        toolrush_worker=toolrush,
        rpc_runner=lambda *args: rpc_calls.append(args),
        clock_ns=Timer(),
    )

    result_a = runner("A", "bounded_read", "warm", 1)
    result_b = runner("B", "bounded_read", "warm", 1)

    assert len(stock.calls) == 1
    assert len(toolrush.calls) == 1
    assert rpc_calls == []
    assert result_a["elapsed_ms"] == 1.0
    assert result_b["elapsed_ms"] == 1.0
    assert result_a["observable"] == result_b["observable"]


def test_operation_runner_uses_rpc_lane_without_falling_back_to_worker():
    stock = Worker("stock")
    toolrush = Worker("toolrush")
    rpc_calls = []

    def rpc_runner(condition, strategy, calls):
        rpc_calls.append((condition, strategy, calls))
        return [{"index": index, "ok": True} for index, _ in enumerate(calls)]

    runner = ToolMicrobenchOperationRunner(
        stock_worker=stock,
        toolrush_worker=toolrush,
        rpc_runner=rpc_runner,
        clock_ns=Timer(),
    )
    a = runner("A", "parallel_read_rpc", "warm", 1)
    b = runner("B", "parallel_read_rpc", "warm", 1)

    assert stock.calls == []
    assert toolrush.calls == []
    assert [call[1] for call in rpc_calls] == ["sequential", "parallel"]
    assert a["observable"] == b["observable"]


def test_operation_runner_fails_closed_when_rpc_lane_is_unbound():
    runner = ToolMicrobenchOperationRunner(
        stock_worker=Worker("stock"),
        toolrush_worker=Worker("toolrush"),
        rpc_runner=None,
        clock_ns=Timer(),
    )
    with pytest.raises(RuntimeError, match="RPC lane is not bound"):
        runner("B", "parallel_read_rpc", "warm", 1)
