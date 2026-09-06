import pytest

from experiments.runtime_acceleration.phase2_rpc import (
    build_worker_rpc_runner,
    execute_rpc_batch,
    validate_rpc_calls,
)
from experiments.runtime_acceleration.runtime_bridge import WORKER_OPERATIONS


def _calls():
    return [
        {"tool": "read_file", "args": {"path": "fixture/source_a.py", "limit": 10}},
        {"tool": "search_files", "args": {"pattern": "benchmark", "path": "fixture"}},
    ]


def test_worker_protocol_exposes_rpc_batch_without_polluting_phase1_handlers():
    assert "rpc_batch" in WORKER_OPERATIONS
    assert {"read", "search", "shell"}.issubset(WORKER_OPERATIONS)


def test_rpc_call_validation_is_read_only_bounded_and_preserves_order():
    calls = validate_rpc_calls(_calls())
    assert calls == _calls()
    assert calls is not _calls()

    with pytest.raises(ValueError, match="1..16"):
        validate_rpc_calls([])
    with pytest.raises(ValueError, match="1..16"):
        validate_rpc_calls(_calls() * 9)
    with pytest.raises(ValueError, match="read_file or search_files"):
        validate_rpc_calls([{"tool": "terminal", "args": {"command": "echo nope"}}])
    with pytest.raises(TypeError, match="args"):
        validate_rpc_calls([{"tool": "read_file", "args": "fixture/source_a.py"}])


def test_sequential_rpc_uses_generated_call_in_input_order():
    observed = []

    def call(tool, args):
        observed.append((tool, args))
        return {"tool": tool, "args": args}

    result = execute_rpc_batch({"_call": call}, "sequential", _calls())
    assert [tool for tool, _ in observed] == ["read_file", "search_files"]
    assert [item["tool"] for item in result] == ["read_file", "search_files"]


def test_parallel_rpc_requires_and_uses_generated_parallel_surface():
    observed = []

    def parallel(calls):
        observed.extend(calls)
        return [{"index": index, "tool": call["tool"]} for index, call in enumerate(calls)]

    result = execute_rpc_batch({"_call": lambda *_: None, "parallel": parallel}, "parallel", _calls())
    assert observed == _calls()
    assert [item["index"] for item in result] == [0, 1]

    with pytest.raises(RuntimeError, match="generated parallel surface"):
        execute_rpc_batch({"_call": lambda *_: None}, "parallel", _calls())


def test_rpc_batch_fails_closed_on_result_error_or_shape_change():
    with pytest.raises(RuntimeError, match="RPC result 0 reported an error"):
        execute_rpc_batch(
            {"_call": lambda *_: {"error": "boom"}},
            "sequential",
            [{"tool": "read_file", "args": {"path": "fixture/source_a.py"}}],
        )
    with pytest.raises(RuntimeError, match="result count mismatch"):
        execute_rpc_batch(
            {"_call": lambda *_: None, "parallel": lambda calls: []},
            "parallel",
            _calls(),
        )


class FakeWorker:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def execute(self, operation, payload):
        self.calls.append((operation, payload))
        assert operation == "rpc_batch"
        return {"results": [{"worker": self.name, "index": index} for index, _ in enumerate(payload["calls"])]}


def test_worker_rpc_runner_selects_exact_condition_worker_and_returns_results_only():
    stock = FakeWorker("stock")
    toolrush = FakeWorker("toolrush")
    runner = build_worker_rpc_runner(stock, toolrush)

    a = runner("A", "sequential", _calls())
    b = runner("B", "parallel", _calls())

    assert [item["worker"] for item in a] == ["stock", "stock"]
    assert [item["worker"] for item in b] == ["toolrush", "toolrush"]
    assert stock.calls[0][1]["strategy"] == "sequential"
    assert toolrush.calls[0][1]["strategy"] == "parallel"

    with pytest.raises(ValueError, match="condition"):
        runner("C", "sequential", _calls())
