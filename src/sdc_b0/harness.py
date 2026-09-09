"""SDC-B0 Task #59: Recursive Planner/Worker Harness — GREEN Implementation.

Protocol source: docs/sdc/b0/2026-09-09-recursive-planner-worker-baseline-protocol.md

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

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable


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


def _compute_process_fingerprint(worktree: Path) -> str:
    """Compute a fingerprint of the worktree state for provenance."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return "unknown"


def _get_git_sha(worktree: Path) -> str:
    """Get current HEAD SHA from worktree."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ""


class B0Harness:
    """Baseline recursive planner/worker harness.

    Implements the B0 topology: root planner dispatches tasks to isolated
    workers via worktrees. Workers return structured handoffs. The planner
    replans based on handoff status.
    """

    def __init__(self, root_goal: str, worktree_base: Path) -> None:
        self.root_goal = root_goal
        self.worktree_base = Path(worktree_base)
        self._workers: dict[str, WorkerExecutor] = {}
        self._plan: list[dict[str, Any]] = []
        self._handoffs: list[WorkerHandoff] = []
        self._planner: Planner | None = None

    def set_planner(self, planner: Planner) -> None:
        """Set the recursive planner for this harness."""
        self._planner = planner

    def register_worker(self, worker_id: str, executor: WorkerExecutor) -> None:
        """Register an isolated worker executor."""
        self._workers[worker_id] = executor

    def run(self) -> list[WorkerHandoff]:
        """Execute the recursive plan, collecting handoffs.

        Returns:
            List of all WorkerHandoffs collected during execution.
        """
        if not self._planner:
            raise RuntimeError("No planner configured")
        if not self._workers:
            raise RuntimeError("No workers registered")

        # Initial plan
        self._plan = self._planner.plan(self.root_goal, {})
        self._handoffs = []

        # Execute until plan is exhausted or all tasks complete/blocked
        max_iterations = len(self._plan) * 3  # safety bound
        iteration = 0

        while self._plan and iteration < max_iterations:
            iteration += 1
            task_spec = self._plan.pop(0)

            # Create isolated worktree
            worktree = self._create_worktree(task_spec.get("task_id", f"task-{iteration}"))

            # Dispatch to worker
            handoff = self._dispatch(task_spec, worktree)
            self._handoffs.append(handoff)

            # Replan if needed
            if self._should_replan(handoff):
                new_tasks = self._planner.replan(handoff, self._plan)
                self._plan.extend(new_tasks)

        return self._handoffs

    def _create_worktree(self, task_id: str) -> Path:
        """Create isolated worktree for a task."""
        worktree_path = self.worktree_base / f"wt-{task_id}"
        worktree_path.mkdir(parents=True, exist_ok=True)
        return worktree_path

    def _dispatch(self, task_spec: dict[str, Any], worktree: Path) -> WorkerHandoff:
        """Dispatch task to appropriate worker."""
        worker_id = task_spec.get("worker_id")
        if not worker_id or worker_id not in self._workers:
            # Round-robin to first available worker
            worker_id = next(iter(self._workers))

        executor = self._workers[worker_id]
        try:
            return executor.execute(task_spec, worktree)
        except Exception as e:
            return WorkerHandoff(
                sender_id=worker_id,
                sender_type="worker",
                task_id=task_spec.get("task_id", "unknown"),
                status=HandoffStatus.FAILED,
                blockers=[str(e)],
                process_fingerprint=_compute_process_fingerprint(worktree),
                base_sha=_get_git_sha(worktree),
                head_sha=_get_git_sha(worktree),
                completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

    def _should_replan(self, handoff: WorkerHandoff) -> bool:
        """Determine if handoff triggers replanning."""
        # Replan on blocked, failed, or stale handoffs
        return handoff.status in (
            HandoffStatus.BLOCKED,
            HandoffStatus.FAILED,
            HandoffStatus.STALE,
        )
