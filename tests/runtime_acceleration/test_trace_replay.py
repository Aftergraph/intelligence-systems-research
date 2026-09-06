import pytest

from experiments.runtime_acceleration.runners.trace_replay import replay_trace, replay_trace_timed
from experiments.runtime_acceleration.traces import load_trace


class Adapter:
    def execute(self, operation, payload):
        return {"operation": operation, "value": payload["value"]}


def test_trace_replay_preserves_order_and_outputs():
    steps = [
        {"operation": "read", "payload": {"value": "a"}},
        {"operation": "search", "payload": {"value": "b"}},
    ]
    assert replay_trace(steps, Adapter()) == [
        {"operation": "read", "value": "a"},
        {"operation": "search", "value": "b"},
    ]


def test_timed_trace_preserves_observable_and_records_nonnegative_elapsed():
    result = replay_trace_timed([{"operation": "read", "payload": {"value": "x"}}], Adapter())
    assert result[0]["observable"] == {"operation": "read", "value": "x"}
    assert result[0]["elapsed_ms"] >= 0


def test_load_trace_rejects_step_without_operation(tmp_path):
    path = tmp_path / "trace.yaml"
    path.write_text("steps:\n  - payload: {value: x}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_trace(path)
