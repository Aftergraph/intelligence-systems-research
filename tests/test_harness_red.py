"""RED tests for SDC-B0 Task #59: Planner/Worker Harness.

Protocol source: docs/sdc/b0/2026-09-09-recursive-planner-worker-baseline-protocol.md

These tests verify the harness skeleton structure exists and raises
NotImplementedError for unimplemented methods (RED phase).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.sdc_b0.harness import (
    B0Harness,
    HandoffStatus,
    WorkerHandoff,
)


class TestB0HarnessRed:
    """RED phase: verify skeleton exists and stubs raise NotImplementedError."""

    def test_handoff_status_enum_values(self) -> None:
        """HandoffStatus must have all protocol-defined values."""
        assert HandoffStatus.COMPLETE_CANDIDATE.value == "complete_candidate"
        assert HandoffStatus.BLOCKED.value == "blocked"
        assert HandoffStatus.FAILED.value == "failed"
        assert HandoffStatus.STALE.value == "stale"

    def test_worker_handoff_dataclass_fields(self) -> None:
        """WorkerHandoff must have all protocol-required fields."""
        handoff = WorkerHandoff(
            sender_id="worker-1",
            sender_type="worker",
            task_id="task-abc",
            status=HandoffStatus.COMPLETE_CANDIDATE,
        )
        assert handoff.sender_id == "worker-1"
        assert handoff.sender_type == "worker"
        assert handoff.task_id == "task-abc"
        assert handoff.status == HandoffStatus.COMPLETE_CANDIDATE
        assert handoff.commands_executed == []
        assert handoff.tests_executed == []
        assert handoff.artifacts == []
        assert handoff.blockers == []
        assert handoff.process_fingerprint == ""
        assert handoff.base_sha == ""
        assert handoff.head_sha == ""

    def test_worker_handoff_to_json(self) -> None:
        """WorkerHandoff.to_json() must produce valid JSON with all fields."""
        handoff = WorkerHandoff(
            sender_id="subplanner-2",
            sender_type="subplanner",
            task_id="task-xyz",
            status=HandoffStatus.BLOCKED,
            blockers=["missing dependency"],
            base_sha="abc123",
            head_sha="def456",
        )
        data = json.loads(handoff.to_json())
        assert data["sender_id"] == "subplanner-2"
        assert data["sender_type"] == "subplanner"
        assert data["status"] == "blocked"
        assert data["blockers"] == ["missing dependency"]
        assert data["base_sha"] == "abc123"
        assert data["head_sha"] == "def456"

    def test_harness_constructor(self, tmp_path: Path) -> None:
        """B0Harness must accept root_goal and worktree_base."""
        harness = B0Harness("test goal", tmp_path)
        assert harness.root_goal == "test goal"
        assert harness.worktree_base == tmp_path

    def test_register_worker_raises(self, tmp_path: Path) -> None:
        """register_worker must raise NotImplementedError in RED phase."""
        harness = B0Harness("test", tmp_path)
        with pytest.raises(NotImplementedError):
            harness.register_worker("w1", None)  # type: ignore

    def test_run_raises(self, tmp_path: Path) -> None:
        """run must raise NotImplementedError in RED phase."""
        harness = B0Harness("test", tmp_path)
        with pytest.raises(NotImplementedError):
            harness.run()

    def test_create_worktree_raises(self, tmp_path: Path) -> None:
        """_create_worktree must raise NotImplementedError in RED phase."""
        harness = B0Harness("test", tmp_path)
        with pytest.raises(NotImplementedError):
            harness._create_worktree("task-1")

    def test_dispatch_raises(self, tmp_path: Path) -> None:
        """_dispatch must raise NotImplementedError in RED phase."""
        harness = B0Harness("test", tmp_path)
        with pytest.raises(NotImplementedError):
            harness._dispatch({}, tmp_path)

    def test_should_replan_raises(self, tmp_path: Path) -> None:
        """_should_replan must raise NotImplementedError in RED phase."""
        harness = B0Harness("test", tmp_path)
        handoff = WorkerHandoff(
            sender_id="w1",
            sender_type="worker",
            task_id="t1",
            status=HandoffStatus.COMPLETE_CANDIDATE,
        )
        with pytest.raises(NotImplementedError):
            harness._should_replan(handoff)
