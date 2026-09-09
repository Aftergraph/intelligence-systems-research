"""SDC-B0 Task #59: Recursive Planner/Worker Harness Skeleton.

Protocol source: docs/sdc/b0/2026-09-09-recursive-planner-worker-baseline-protocol.md
Status: RED skeleton — methods raise NotImplementedError until GREEN phase.

This harness implements the B0 baseline topology:
  ROOT PLANNER → SUBPLANNER(s) → WORKER(s)

Key invariants (B0, no governance):
- Workers operate in isolated worktrees
- Handoffs are structured JSON, one-way upward
- No peer-to-peer worker communication
- Root planner owns full scope, does no implementation
- Continuous replanning from fresh handoffs
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


class HandoffStatus(str, Enum):
    COMPLETE_CANDIDATE = "complete_candidate"
    BLOCKED = "blocked"
    FAILED = "failed"
    STALE = "stale"


@dataclass(frozen=True)
class WorkerHandoff:
    """Structured handoff from worker/subplanner to parent."""
    sender_id: str
    sender_type: str  # "worker" | "subplanner"
    task_id: str
    status: HandoffStatus
    commands_executed: list[dict[str, Any]] = field(default_factory=list)
    tests_executed: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    process_fingerprint: str = ""
    base_sha: str = ""
    head_sha: str = ""
    completed_at: str = ""

    def to_json(self) -> str:
        return json.dumps({
            "sender_id": self.sender_id,
            "sender_type": self.sender_type,
            "task_id": self.task_id,
            "status": self.status.value,
            "commands_executed": self.commands_executed,
            "tests_executed": self.tests_executed,
            "artifacts": self.artifacts,
            "blockers": self.blockers,
            "process_fingerprint": self.process_fingerprint,
            "base_sha": self.base_sha,
            "head_sha": self.head_sha,
            "completed_at": self.completed_at,
        }, indent=2)


@runtime_checkable
class WorkerExecutor(Protocol):
    """Protocol for isolated worker execution."""
    def execute(self, task_spec: dict[str, Any], worktree: Path) -> WorkerHandoff: ...


@runtime_checkable
class Planner(Protocol):
    """Protocol for recursive planner."""
    def plan(self, goal: str, context: dict[str, Any]) -> list[dict[str, Any]]: ...
    def replan(self, handoff: WorkerHandoff, current_plan: list[dict[str, Any]]) -> list[dict[str, Any]]: ...


class B0Harness:
    """Baseline recursive planner/worker harness.

    This is the RED skeleton. All core methods raise NotImplementedError
    until the GREEN implementation phase.
    """

    def __init__(self, root_goal: str, worktree_base: Path) -> None:
        self.root_goal = root_goal
        self.worktree_base = worktree_base
        self._workers: dict[str, WorkerExecutor] = {}
        self._plan: list[dict[str, Any]] = []

    def register_worker(self, worker_id: str, executor: WorkerExecutor) -> None:
        """Register an isolated worker executor."""
        raise NotImplementedError("B0 Harness RED skeleton")

    def run(self) -> list[WorkerHandoff]:
        """Execute the recursive plan, collecting handoffs."""
        raise NotImplementedError("B0 Harness RED skeleton")

    def _create_worktree(self, task_id: str) -> Path:
        """Create isolated worktree for a task."""
        raise NotImplementedError("B0 Harness RED skeleton")

    def _dispatch(self, task_spec: dict[str, Any], worktree: Path) -> WorkerHandoff:
        """Dispatch task to appropriate worker."""
        raise NotImplementedError("B0 Harness RED skeleton")

    def _should_replan(self, handoff: WorkerHandoff) -> bool:
        """Determine if handoff triggers replanning."""
        raise NotImplementedError("B0 Harness RED skeleton")
