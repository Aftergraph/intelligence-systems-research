"""Tests for SDC-B0 Task #74: failed-worker recovery and stale-base handling.

These tests verify the B0Harness correctly handles:
- HandoffStatus.FAILED: retry with reassignment, max_retries cap, telemetry
- HandoffStatus.STALE: record event, rebase or skip, telemetry
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
from src.sdc_b0.telemetry import TelemetryCollector


# ---------------------------------------------------------------------------
# Mock fixtures
# ---------------------------------------------------------------------------

class FailingWorker:
    """Worker that always returns FAILED, with configurable attempt count."""

    def __init__(self, fail_count: int = 3):
        self._fail_count = fail_count
        self.attempts: list[tuple[dict, Path]] = []
        self._call_index = 0

    def execute(self, task_spec: dict[str, Any], worktree: Path) -> WorkerHandoff:
        self.attempts.append((task_spec, worktree))
        if self._call_index < self._fail_count:
            self._call_index += 1
            return WorkerHandoff(
                sender_id="failing-worker",
                sender_type="worker",
                task_id=task_spec.get("task_id", "unknown"),
                status=HandoffStatus.FAILED,
                blockers=["simulated failure"],
                base_sha="abc123",
                head_sha="def456",
            )
        # Succeed after fail_count attempts
        self._call_index += 1
        return WorkerHandoff(
            sender_id="failing-worker",
            sender_type="worker",
            task_id=task_spec.get("task_id", "unknown"),
            status=HandoffStatus.COMPLETE_CANDIDATE,
            base_sha="abc123",
            head_sha="def456",
        )


class StaleWorker:
    """Worker that always returns STALE."""

    def __init__(self, blockers: list[str] | None = None):
        self.blockers = blockers or ["base SHA diverged"]
        self.calls: list[tuple[dict, Path]] = []

    def execute(self, task_spec: dict[str, Any], worktree: Path) -> WorkerHandoff:
        self.calls.append((task_spec, worktree))
        return WorkerHandoff(
            sender_id="stale-worker",
            sender_type="worker",
            task_id=task_spec.get("task_id", "unknown"),
            status=HandoffStatus.STALE,
            blockers=self.blockers,
            base_sha="old_sha",
            head_sha="new_sha",
        )


class SuccessWorker:
    """Worker that always returns COMPLETE_CANDIDATE."""

    def __init__(self):
        self.calls: list[tuple[dict, Path]] = []

    def execute(self, task_spec: dict[str, Any], worktree: Path) -> WorkerHandoff:
        self.calls.append((task_spec, worktree))
        return WorkerHandoff(
            sender_id="success-worker",
            sender_type="worker",
            task_id=task_spec.get("task_id", "unknown"),
            status=HandoffStatus.COMPLETE_CANDIDATE,
            base_sha="abc",
            head_sha="def",
        )


class RebaseSucceedingWorker:
    """Worker that returns STALE, then succeeds after rebase (simulated)."""

    def __init__(self):
        self.calls: list[tuple[dict, Path]] = []
        self.stale_then_success = True

    def execute(self, task_spec: dict[str, Any], worktree: Path) -> WorkerHandoff:
        self.calls.append((task_spec, worktree))
        if self.stale_then_success:
            self.stale_then_success = False
            return WorkerHandoff(
                sender_id="rebase-worker",
                sender_type="worker",
                task_id=task_spec.get("task_id", "unknown"),
                status=HandoffStatus.STALE,
                blockers=["base SHA diverged"],
                base_sha="old_sha",
                head_sha="new_sha",
            )
        return WorkerHandoff(
            sender_id="rebase-worker",
            sender_type="worker",
            task_id=task_spec.get("task_id", "unknown"),
            status=HandoffStatus.COMPLETE_CANDIDATE,
            base_sha="rebased_sha",
            head_sha="rebase_head_sha",
        )


class MockPlanner:
    """Mock planner that returns a fixed initial plan and no replan tasks."""

    def __init__(self, initial_plan: list[dict] | None = None):
        self._initial_plan = initial_plan or []
        self.replan_calls: list[tuple[WorkerHandoff, list]] = []

    def plan(self, goal: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        return list(self._initial_plan)

    def replan(
        self, handoff: WorkerHandoff, current_plan: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        self.replan_calls.append((handoff, current_plan))
        return []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_workdir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def telemetry_collector(tmp_path: Path) -> TelemetryCollector:
    return TelemetryCollector(run_id="test-run", log_dir=tmp_path / "telemetry")


# ===========================================================================
# FAILED handling tests
# ===========================================================================

class TestFailedWorkerRecovery:
    """Tests for HandoffStatus.FAILED retry and reassignment."""

    def test_failed_worker_retries_and_succeeds(self, tmp_workdir: Path):
        """FAILED worker retries up to max_retries and succeeds when it recovers."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        worker = FailingWorker(fail_count=2)  # fails twice, then succeeds
        harness.register_worker("w1", worker)
        harness.set_max_retries(3)

        handoffs = harness.run()

        assert len(handoffs) == 1
        assert handoffs[0].status == HandoffStatus.COMPLETE_CANDIDATE
        assert len(worker.attempts) == 3  # 2 fails + 1 success
        assert harness.failed_retry_counts()["t1"] == 2

    def test_failed_worker_exhausts_retries(self, tmp_workdir: Path):
        """FAILED worker exhausts max_retries and returns FAILED handoff."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        worker = FailingWorker(fail_count=10)  # never recovers
        harness.register_worker("w1", worker)
        harness.set_max_retries(2)

        handoffs = harness.run()

        assert len(handoffs) == 1
        assert handoffs[0].status == HandoffStatus.FAILED
        assert len(worker.attempts) == 3  # 1 initial + 2 retries
        assert harness.failed_retry_counts()["t1"] == 3

    def test_failed_worker_reassigns_to_different_worker(self, tmp_workdir: Path):
        """FAILED worker reassigns to a different worker on retry."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        worker1 = FailingWorker(fail_count=1)
        worker2 = SuccessWorker()
        harness.register_worker("w1", worker1)
        harness.register_worker("w2", worker2)
        harness.set_max_retries(3)

        handoffs = harness.run()

        assert len(handoffs) == 1
        assert handoffs[0].status == HandoffStatus.COMPLETE_CANDIDATE
        # worker1 failed once, then reassigned to worker2
        assert len(worker1.attempts) == 1
        assert len(worker2.calls) == 1

    def test_failed_worker_only_one_worker_retries_in_place(self, tmp_workdir: Path):
        """FAILED worker retries on same worker when no other workers available."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        worker = FailingWorker(fail_count=1)
        harness.register_worker("w1", worker)
        harness.set_max_retries(3)

        handoffs = harness.run()

        assert len(handoffs) == 1
        assert handoffs[0].status == HandoffStatus.COMPLETE_CANDIDATE
        assert len(worker.attempts) == 2  # 1 fail + 1 success

    def test_max_retries_setter_validation(self, tmp_workdir: Path):
        """set_max_retries rejects negative values."""
        harness = B0Harness("test", tmp_workdir)
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            harness.set_max_retries(-1)

    def test_failed_sensor_emits_telemetry(self, tmp_workdir: Path, telemetry_collector: TelemetryCollector):
        """FAILED retry events are emitted to telemetry."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        worker = FailingWorker(fail_count=1)
        harness.register_worker("w1", worker)
        harness.set_telemetry(telemetry_collector)
        harness.set_max_retries(3)

        harness.run()

        # Read the telemetry log
        log_path = telemetry_collector._log_path
        events = []
        with open(log_path) as f:
            for line in f:
                events.append(json.loads(line))

        event_types = [e["event"] for e in events]
        assert "worker_failed_retry" in event_types
        # The retry event should have the right task_id
        retry_events = [e for e in events if e["event"] == "worker_failed_retry"]
        assert any(e.get("task_id") == "t1" for e in retry_events)

    def test_failed_exhausted_emits_telemetry(self, tmp_workdir: Path, telemetry_collector: TelemetryCollector):
        """worker_failed_exhausted is emitted when max retries exceeded."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        worker = FailingWorker(fail_count=10)
        harness.register_worker("w1", worker)
        harness.set_telemetry(telemetry_collector)
        harness.set_max_retries(1)

        harness.run()

        log_path = telemetry_collector._log_path
        events = []
        with open(log_path) as f:
            for line in f:
                events.append(json.loads(line))

        event_types = [e["event"] for e in events]
        assert "worker_failed_exhausted" in event_types


# ===========================================================================
# STALE handling tests
# ===========================================================================

class TestStaleBaseHandling:
    """Tests for HandoffStatus.STALE rebase/skip handling."""

    def test_stale_base_skip_handler(self, tmp_workdir: Path):
        """STALE worker with skip handler returns SKIPPED handoff."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        harness.set_stale_base_handler("skip")
        worker = StaleWorker()
        harness.register_worker("w1", worker)

        handoffs = harness.run()

        assert len(handoffs) == 1
        assert handoffs[0].status == HandoffStatus.SKIPPED
        assert "stale_base" in handoffs[0].blockers[0]

    def test_stale_events_recorded(self, tmp_workdir: Path):
        """STALE events are recorded in the harness."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        harness.set_stale_base_handler("skip")
        worker = StaleWorker(blockers=["SHA mismatch"])
        harness.register_worker("w1", worker)

        harness.run()

        events = harness.stale_events()
        assert len(events) == 1
        assert events[0]["task_id"] == "t1"
        assert events[0]["blockers"] == ["SHA mismatch"]
        assert events[0]["base_sha"] == "old_sha"

    def test_stale_base_handler_validation(self, tmp_workdir: Path):
        """set_stale_base_handler rejects unknown values."""
        harness = B0Harness("test", tmp_workdir)
        with pytest.raises(ValueError, match="Unknown stale handler"):
            harness.set_stale_base_handler("invalid")

    def test_stale_base_default_is_rebase(self, tmp_workdir: Path):
        """Default stale_base_handler is 'rebase'."""
        harness = B0Harness("test", tmp_workdir)
        # Default is "rebase" — but we can't test actual rebase without a git repo.
        # Just verify the attribute is set.
        assert harness._stale_base_handler == "rebase"

    def test_stale_worker_calls_once_with_skip(self, tmp_workdir: Path):
        """STALE worker called once when skip handler is active."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        harness.set_stale_base_handler("skip")
        worker = StaleWorker()
        harness.register_worker("w1", worker)

        harness.run()

        assert len(worker.calls) == 1

    def test_stale_base_handler_skip_emits_telemetry(self, tmp_workdir: Path, telemetry_collector: TelemetryCollector):
        """STALE skip emits stale_base_detected and stale_base_skipped events."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        harness.set_stale_base_handler("skip")
        harness.set_telemetry(telemetry_collector)
        worker = StaleWorker()
        harness.register_worker("w1", worker)

        harness.run()

        log_path = telemetry_collector._log_path
        events = []
        with open(log_path) as f:
            for line in f:
                events.append(json.loads(line))

        event_types = [e["event"] for e in events]
        assert "stale_base_detected" in event_types
        assert "stale_base_skipped" in event_types

    def test_multiple_failed_tasks_independent_retries(self, tmp_workdir: Path):
        """Multiple tasks with FAILED workers get independent retry counts.

        Uses separate FailingWorker instances per task so state doesn't
        interfere, and verifies retry counts are tracked independently.
        """
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([
            {"task_id": "t1", "worker_id": "w1"},
            {"task_id": "t2", "worker_id": "w2"},
        ]))
        # w1 fails once then succeeds; w2 never fails
        harness.register_worker("w1", FailingWorker(fail_count=1))
        harness.register_worker("w2", SuccessWorker())
        harness.set_max_retries(3)

        handoffs = harness.run()

        assert len(handoffs) == 2
        assert handoffs[0].status == HandoffStatus.COMPLETE_CANDIDATE
        assert handoffs[1].status == HandoffStatus.COMPLETE_CANDIDATE
        # t1 on w1: w1 fails once, then retries and succeeds = 1 retry
        assert harness.failed_retry_counts()["t1"] == 1
        # t2 on w2: never fails = 0 retries (may not be in dict)
        counts = harness.failed_retry_counts()
        assert counts.get("t2", 0) == 0


# ===========================================================================
# Telemetry integration tests
# ===========================================================================

class TestTelemetryIntegration:
    """Tests verifying telemetry events are emitted for FAILED/STALE paths."""

    def test_telemetry_log_contains_all_failed_events(
        self, tmp_workdir: Path, telemetry_collector: TelemetryCollector
    ):
        """All failed-retry events appear in the telemetry log."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        worker = FailingWorker(fail_count=2)
        harness.register_worker("w1", worker)
        harness.set_telemetry(telemetry_collector)
        harness.set_max_retries(3)

        harness.run()

        with open(telemetry_collector._log_path) as f:
            lines = f.readlines()

        events = [json.loads(line) for line in lines]
        assert any(e["event"] == "worker_failed_retry" for e in events)

    def test_telemetry_log_contains_stale_events(
        self, tmp_workdir: Path, telemetry_collector: TelemetryCollector
    ):
        """All stale-base events appear in the telemetry log."""
        harness = B0Harness("test goal", tmp_workdir)
        harness.set_planner(MockPlanner([{"task_id": "t1", "worker_id": "w1"}]))
        harness.set_stale_base_handler("skip")
        harness.set_telemetry(telemetry_collector)
        worker = StaleWorker()
        harness.register_worker("w1", worker)

        harness.run()

        with open(telemetry_collector._log_path) as f:
            lines = f.readlines()

        events = [json.loads(line) for line in lines]
        assert any(e["event"] == "stale_base_detected" for e in events)
        assert any(e["event"] == "stale_base_skipped" for e in events)

    def test_telemetry_closed_cleanly(self, tmp_workdir: Path):
        """Telemetry collector closes cleanly after harness run."""
        collector = TelemetryCollector(run_id="test-close", log_dir=tmp_workdir / "tel")
        collector.emit("test_event", {"key": "value"})
        collector.close()
        # Should not raise
        collector.close()  # idempotent
