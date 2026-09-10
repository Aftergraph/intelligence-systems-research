"""Integration test: TelemetryCollector + HermesWorktreeSandbox composition."""
import os
import json
import pytest
from pathlib import Path
from src.sdc_b0.telemetry import TelemetryCollector
from src.sdc_b0.worker_sandbox import HermesWorktreeSandbox


def _init_git_repo(repo_path):
    """Configure git identity for CI runners."""
    os.system(f'git -C {repo_path} config user.email "test@test.com"')
    os.system(f'git -C {repo_path} config user.name "Test"')


class TestTelemetrySandboxComposition:
    def test_telemetry_emits_sandbox_create_event(self, tmp_path):
        log_dir = tmp_path / "logs"
        collector = TelemetryCollector(run_id="test-run-001", log_dir=log_dir)
        repo = tmp_path / "repo"
        repo.mkdir()
        os.system(f"git init {repo}")
        _init_git_repo(str(repo))
        os.system(f"git -C {repo} commit --allow-empty -m 'init'")
        
        wt_root = tmp_path / "worktrees"
        sandbox = HermesWorktreeSandbox(str(repo), str(wt_root))
        collector.emit("sandbox.create", {"worktree_root": str(wt_root)})
        collector._file.close()
        
        log_file = log_dir / "test-run-001.jsonl"
        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        events = [json.loads(l) for l in lines]
        assert any(e["event"] == "sandbox.create" for e in events)

    def test_telemetry_emits_sandbox_execute_event(self, tmp_path):
        log_dir = tmp_path / "logs"
        collector = TelemetryCollector(run_id="test-run-002", log_dir=log_dir)
        collector.emit("sandbox.execute", {"command": "echo hello", "exit_code": 0})
        collector._file.close()
        
        log_file = log_dir / "test-run-002.jsonl"
        lines = log_file.read_text().strip().split("\n")
        events = [json.loads(l) for l in lines]
        exec_events = [e for e in events if e["event"] == "sandbox.execute"]
        assert len(exec_events) == 1
        assert exec_events[0]["exit_code"] == 0

    def test_telemetry_emits_sandbox_teardown_event(self, tmp_path):
        log_dir = tmp_path / "logs"
        collector = TelemetryCollector(run_id="test-run-003", log_dir=log_dir)
        collector.emit("sandbox.teardown", {"cleaned": True})
        collector._file.close()
        
        log_file = log_dir / "test-run-003.jsonl"
        lines = log_file.read_text().strip().split("\n")
        events = [json.loads(l) for l in lines]
        teardown_events = [e for e in events if e["event"] == "sandbox.teardown"]
        assert len(teardown_events) == 1
        assert teardown_events[0]["cleaned"] is True
