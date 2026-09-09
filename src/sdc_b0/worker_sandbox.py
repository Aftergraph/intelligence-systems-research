"""SDC-B0 Task #61: WorkerSandbox Interface.

Protocol source: docs/sdc/b0/2026-09-09-recursive-planner-worker-baseline-protocol.md
Smoke run spec: docs/sdc/b0/2026-09-09-smoke-run-specification.md

The WorkerSandbox defines the canonical interface for isolated worker execution.
B0 canonical backend: HermesWorktreeSandbox (git worktree-based isolation).
"""
from __future__ import annotations

import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SandboxResult:
    """Immutable result from a sandboxed worker execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    worktree_path: Path
    base_sha: str
    head_sha: str


class WorkerSandbox(ABC):
    """Abstract interface for isolated worker execution environments."""

    @abstractmethod
    def create(self, task_id: str, base_sha: str) -> Path:
        """Create an isolated workspace for a worker task."""

    @abstractmethod
    def execute(
        self,
        task_id: str,
        command: str,
        *,
        timeout_seconds: float = 300.0,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute a command in the sandboxed workspace."""

    @abstractmethod
    def teardown(self, task_id: str) -> None:
        """Remove the sandboxed workspace. Idempotent."""

    @abstractmethod
    def list_active(self) -> list[str]:
        """Return list of active task_ids with live sandboxes."""


class HermesWorktreeSandbox(WorkerSandbox):
    """Git worktree-based sandbox for B0 workers.

    Each worker gets an isolated git worktree branched from base_sha.
    Worktrees are created under a configurable root directory.
    """

    def __init__(self, repo_path: Path, worktree_root: Path) -> None:
        self._repo_path = Path(repo_path)
        self._worktree_root = Path(worktree_root)
        self._worktree_root.mkdir(parents=True, exist_ok=True)
        self._active: dict[str, Path] = {}

    def create(self, task_id: str, base_sha: str) -> Path:
        wt_path = self._worktree_root / task_id
        subprocess.run(
            ["git", "-C", str(self._repo_path), "worktree", "add", "-b", f"sdc-worker-{task_id}", str(wt_path), base_sha],
            check=True,
            capture_output=True,
            text=True,
        )
        self._active[task_id] = wt_path
        return wt_path

    def execute(
        self,
        task_id: str,
        command: str,
        *,
        timeout_seconds: float = 300.0,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        if task_id not in self._active:
            raise KeyError(f"No active sandbox for task '{task_id}'")
        wt_path = self._active[task_id]
        start = time.monotonic()
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(wt_path),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            head_sha = subprocess.run(
                ["git", "-C", str(wt_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            base_sha = subprocess.run(
                ["git", "-C", str(wt_path), "merge-base", "HEAD", "main"],
                capture_output=True,
                text=True,
            ).stdout.strip() or head_sha
            return SandboxResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_ms=duration_ms,
                worktree_path=wt_path,
                base_sha=base_sha,
                head_sha=head_sha,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start) * 1000)
            return SandboxResult(
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout_seconds}s",
                duration_ms=duration_ms,
                worktree_path=wt_path,
                base_sha="",
                head_sha="",
            )

    def teardown(self, task_id: str) -> None:
        wt_path = self._active.pop(task_id, None)
        if wt_path is None:
            return
        try:
            subprocess.run(
                ["git", "-C", str(self._repo_path), "worktree", "remove", "--force", str(wt_path)],
                capture_output=True,
                text=True,
            )
        except Exception:
            pass
        # Clean up branch if it exists
        try:
            subprocess.run(
                ["git", "-C", str(self._repo_path), "branch", "-D", f"sdc-worker-{task_id}"],
                capture_output=True,
                text=True,
            )
        except Exception:
            pass

    def list_active(self) -> list[str]:
        return list(self._active.keys())
