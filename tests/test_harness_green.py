"""GREEN tests for SDC-B0 Task #59: Planner/Worker Harness.

Protocol source: docs/sdc/b0/2026-09-09-recursive-planner-worker-baseline-protocol.md

These tests verify the harness implementation works correctly.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.sdc_b0.harness import (
    B0Harness,
    HandoffStatus,
    WorkerHandoff,
)


class MockWorker:
    """Mock worker executor for testing."""
    def __init__(self, status: HandoffStatus = HandoffStatus.COMPLETE_CANDIDATE):
        self._status = status
        self.calls: list[tuple[dict, Path]] = []

    def execute(self, task_spec: dict[str, Any], worktree: Path) -> WorkerHandoff:
        self.calls.append((task_spec, worktree))
        return WorkerHandoff(
            sender_id="mock-worker",
            sender_type="worker",
            task_id=task_spec.get("task_id", "unknown"),
            status=self._status,
            base_sha="abc123",
            head_sha="def456",
        )


class MockPlanner:
    """Mock planner for testing."""
    def __init__(self, initial_plan: list[dict] | None = None):
        self._initial_plan = initial_plan or []
        self.replan_calls: list[tuple[WorkerHandoff, list]] = []

    def plan(self, goal: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        return list(self._initial_plan)

    def replan(self, handoff: WorkerHandoff, current_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.replan_calls.append((handoff, current_plan))
        return []  # No additional tasks by default


class TestB0HarnessGreen:
    """GREEN phase: verify harness implementation."""

    def test_register_worker(self, tmp_path: Path) -> None:
        """register_worker must store worker executors."""
        harness = B0Harness("test", tmp_path)
        worker = MockWorker()
        harness.register_worker("w1", worker)
        assert "w1" in harness._workers

    def test_run_requires_planner(self, tmp_path: Path) -> None:
        """run must raise if no planner configured."""
        harness = B0Harness("test", tmp_path)
        harness.register_worker("w1", MockWorker())
        with pytest.raises(RuntimeError, match="No planner"):
            harness.run()

    def test_run_requires_workers(self, tmp_path: Path) -> None:
        """run must raise if no workers registered."""
        harness = B0Harness("test", tmp_path)
        harness.set_planner(MockPlanner())
        with pytest.raises(RuntimeError, match="No workers"):
            harness.run()

    def test_run_dispatches_to_worker(self, tmp_path: Path) -> None:
        """run must dispatch tasks to registered workers."""
        plan = [{"task_id": "t1", "worker_id": "w1"}]
        harness = B0Harness("test goal", tmp_path)
        harness.set_planner(MockPlanner(plan))
        worker = MockWorker()
        harness.register_worker("w1", worker)

        handoffs = harness.run()

        assert len(handoffs) == 1
        assert handoffs[0].task_id == "t1"
        assert handoffs[0].status == HandoffStatus.COMPLETE_CANDIDATE
        assert len(worker.calls) == 1

    def test_create_worktree_creates_directory(self, tmp_path: Path) -> None:
        """_create_worktree must create isolated directory."""
        harness = B0Harness("test", tmp_path)
        wt = harness._create_worktree("task-xyz")
        assert wt.exists()
        assert wt.is_dir()
        assert "wt-task-xyz" in str(wt)

    def test_should_replan_on_blocked(self, tmp_path: Path) -> None:
        """_should_replan must return True for BLOCKED handoffs."""
        harness = B0Harness("test", tmp_path)
        handoff = WorkerHandoff(
            sender_id="w1",
            sender_type="worker",
            task_id="t1",
            status=HandoffStatus.BLOCKED,
        )
        assert harness._should_replan(handoff) is True

    def test_should_replan_on_failed(self, tmp_path: Path) -> None:
        """_should_replan must return True for FAILED handoffs."""
        harness = B0Harness("test", tmp_path)
        handoff = WorkerHandoff(
            sender_id="w1",
            sender_type="worker",
            task_id="t1",
            status=HandoffStatus.FAILED,
        )
        assert harness._should_replan(handoff) is True

    def test_should_not_replan_on_complete(self, tmp_path: Path) -> None:
        """_should_replan must return False for COMPLETE_CANDIDATE."""
        harness = B0Harness("test", tmp_path)
        handoff = WorkerHandoff(
            sender_id="w1",
            sender_type="worker",
            task_id="t1",
            status=HandoffStatus.COMPLETE_CANDIDATE,
        )
        assert harness._should_replan(handoff) is False

    def test_handoff_json_serialization(self) -> None:
        """WorkerHandoff.to_json must produce valid JSON."""
        handoff = WorkerHandoff(
            sender_id="w1",
            sender_type="worker",
            task_id="t1",
            status=HandoffStatus.COMPLETE_CANDIDATE,
            commands_executed=[{"cmd": "echo hello", "exit_code": 0}],
            base_sha="abc",
            head_sha="def",
        )
        data = json.loads(handoff.to_json())
        assert data["sender_id"] == "w1"
        assert data["commands_executed"] == [{"cmd": "echo hello", "exit_code": 0}]
        assert data["base_sha"] == "abc"
