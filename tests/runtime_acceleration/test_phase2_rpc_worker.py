from experiments.runtime_acceleration.hermes_host_worker import dispatch_operation


class RpcHarness:
    def __init__(self):
        self.calls = []

    def execute(self, strategy, calls):
        self.calls.append((strategy, calls))
        return [{"index": index, "tool": call["tool"]} for index, call in enumerate(calls)]


def test_worker_dispatch_routes_rpc_batch_only_through_generated_rpc_harness():
    harness = RpcHarness()
    payload = {
        "strategy": "parallel",
        "calls": [
            {"tool": "read_file", "args": {"path": "fixture/source_a.py", "limit": 10}},
            {"tool": "search_files", "args": {"pattern": "benchmark", "path": "fixture"}},
        ],
    }
    result = dispatch_operation(
        "rpc_batch",
        payload,
        workspace=".",
        file_tools=None,
        environment=None,
        task_id="test",
        rpc_harness=harness,
    )
    assert result == {
        "results": [
            {"index": 0, "tool": "read_file"},
            {"index": 1, "tool": "search_files"},
        ]
    }
    assert harness.calls == [("parallel", payload["calls"])]


def test_worker_rpc_batch_requires_initialized_harness():
    try:
        dispatch_operation(
            "rpc_batch",
            {"strategy": "sequential", "calls": [{"tool": "read_file", "args": {}}]},
            workspace=".",
            file_tools=None,
            environment=None,
            task_id="test",
            rpc_harness=None,
        )
    except RuntimeError as exc:
        assert "RPC harness is not initialized" in str(exc)
    else:
        raise AssertionError("rpc_batch must fail closed without generated RPC harness")
