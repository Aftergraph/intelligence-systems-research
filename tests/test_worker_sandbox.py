"""GREEN tests for SDC-B0 Task #61: WorkerSandbox Interface.

Protocol source: docs/sdc/b0/2026-09-09-recursive-planner-worker-baseline-protocol.md
Smoke run spec: docs/sdc/b0/2026-09-09-smoke-run-specification.md
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _init_git_repo(repo: Path) -> str:
    """Initialize a minimal git repo and return HEAD SHA."""
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test.com"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "--allow-empty", "-m", "init"], check=True, capture_output=True)
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


class TestHermesWorktreeSandboxGreen:
    """GREEN phase: verify HermesWorktreeSandbox implementation."""

    def test_create_returns_worktree_path(self, tmp_path: Path) -> None:
        from src.sdc_b0.worker_sandbox import HermesWorktreeSandbox

        repo = tmp_path / "repo"
        repo.mkdir()
        wt_root = tmp_path / "worktrees"
        base_sha = _init_git_repo(repo)

        sandbox = HermesWorktreeSandbox(repo, wt_root)
        wt_path = sandbox.create("task-001", base_sha)

        assert wt_path.exists()
        assert wt_path.is_dir()
        assert "task-001" in str(wt_path)
        sandbox.teardown("task-001")

    def test_execute_runs_command_in_worktree(self, tmp_path: Path) -> None:
        from src.sdc_b0.worker_sandbox import HermesWorktreeSandbox

        repo = tmp_path / "repo"
        repo.mkdir()
        wt_root = tmp_path / "worktrees"
        base_sha = _init_git_repo(repo)

        sandbox = HermesWorktreeSandbox(repo, wt_root)
        sandbox.create("task-002", base_sha)

        result = sandbox.execute("task-002", "echo hello-world")

        assert result.exit_code == 0
        assert "hello-world" in result.stdout
        assert result.base_sha == base_sha
        assert result.duration_ms >= 0
        sandbox.teardown("task-002")

    def test_execute_captures_stderr(self, tmp_path: Path) -> None:
        from src.sdc_b0.worker_sandbox import HermesWorktreeSandbox

        repo = tmp_path / "repo"
        repo.mkdir()
        wt_root = tmp_path / "worktrees"
        base_sha = _init_git_repo(repo)

        sandbox = HermesWorktreeSandbox(repo, wt_root)
        sandbox.create("task-003", base_sha)

        result = sandbox.execute("task-003", "echo err-msg >&2; exit 1")

        assert result.exit_code == 1
        assert "err-msg" in result.stderr
        sandbox.teardown("task-003")

    def test_teardown_removes_worktree(self, tmp_path: Path) -> None:
        from src.sdc_b0.worker_sandbox import HermesWorktreeSandbox

        repo = tmp_path / "repo"
        repo.mkdir()
        wt_root = tmp_path / "worktrees"
        base_sha = _init_git_repo(repo)

        sandbox = HermesWorktreeSandbox(repo, wt_root)
        wt_path = sandbox.create("task-004", base_sha)
        assert wt_path.exists()

        sandbox.teardown("task-004")
        assert not wt_path.exists()

    def test_teardown_is_idempotent(self, tmp_path: Path) -> None:
        from src.sdc_b0.worker_sandbox import HermesWorktreeSandbox

        repo = tmp_path / "repo"
        repo.mkdir()
        wt_root = tmp_path / "worktrees"
        base_sha = _init_git_repo(repo)

        sandbox = HermesWorktreeSandbox(repo, wt_root)
        sandbox.create("task-005", base_sha)
        sandbox.teardown("task-005")
        sandbox.teardown("task-005")  # Should not raise

    def test_list_active_tracks_created_sandboxes(self, tmp_path: Path) -> None:
        from src.sdc_b0.worker_sandbox import HermesWorktreeSandbox

        repo = tmp_path / "repo"
        repo.mkdir()
        wt_root = tmp_path / "worktrees"
        base_sha = _init_git_repo(repo)

        sandbox = HermesWorktreeSandbox(repo, wt_root)
        assert sandbox.list_active() == []

        sandbox.create("task-006", base_sha)
        assert "task-006" in sandbox.list_active()

        sandbox.create("task-007", base_sha)
        active = sandbox.list_active()
        assert "task-006" in active
        assert "task-007" in active

        sandbox.teardown("task-006")
        assert "task-006" not in sandbox.list_active()
        assert "task-007" in sandbox.list_active()

        sandbox.teardown("task-007")

    def test_execute_unknown_task_raises(self, tmp_path: Path) -> None:
        from src.sdc_b0.worker_sandbox import HermesWorktreeSandbox

        repo = tmp_path / "repo"
        repo.mkdir()
        wt_root = tmp_path / "worktrees"

        sandbox = HermesWorktreeSandbox(repo, wt_root)

        with pytest.raises(KeyError, match="unknown-task"):
            sandbox.execute("unknown-task", "echo nope")

    def test_sandbox_result_is_frozen(self, tmp_path: Path) -> None:
        from src.sdc_b0.worker_sandbox import SandboxResult

        result = SandboxResult(
            exit_code=0,
            stdout="out",
            stderr="",
            duration_ms=10,
            worktree_path=tmp_path,
            base_sha="abc",
            head_sha="def",
        )

        with pytest.raises(AttributeError):
            result.exit_code = 1  # type: ignore[misc]
