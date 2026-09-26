from __future__ import annotations

from jev_engineering.execution_context import WorksExecutionContext


def test_execution_context_is_stable_serializable_and_parent_bound() -> None:
    root = WorksExecutionContext.create(mission_id="m1", node_id="n1", principal="worker:a")
    child = WorksExecutionContext.create(
        mission_id="m1", node_id="n2", principal="worker:b",
        trace_id=root.trace_id, parent_execution_context_id=root.execution_context_id,
    )
    assert root.execution_context_id.startswith("exec_")
    assert root.trace_id.startswith("trace_")
    assert child.trace_id == root.trace_id
    assert child.parent_execution_context_id == root.execution_context_id
    assert WorksExecutionContext.from_dict(child.to_dict()) == child
