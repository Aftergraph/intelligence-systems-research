"""GREEN tests for SDC-B0 Task #60: Telemetry Collector.

Protocol source: docs/sdc/b0/2026-09-09-vds-execution-telemetry-schema.md
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestTelemetryCollectorGreen:
    """GREEN phase: verify telemetry collector implementation."""

    def test_constructor_creates_log_dir(self, tmp_path: Path) -> None:
        from src.sdc_b0.telemetry import TelemetryCollector
        log_dir = tmp_path / "logs"
        tc = TelemetryCollector("run-001", log_dir)
        assert log_dir.exists()
        tc.close()

    def test_emit_writes_jsonl(self, tmp_path: Path) -> None:
        from src.sdc_b0.telemetry import TelemetryCollector
        tc = TelemetryCollector("run-002", tmp_path / "logs")
        tc.emit("test_event", {"key": "value"})
        tc.close()

        log_file = tmp_path / "logs" / "run-002.jsonl"
        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["event"] == "test_event"
        assert event["key"] == "value"
        assert "timestamp" in event

    def test_emit_run_start(self, tmp_path: Path) -> None:
        from src.sdc_b0.telemetry import TelemetryCollector
        tc = TelemetryCollector("run-003", tmp_path / "logs")
        tc.emit_run_start(mission="test-mission", vds_fingerprint="fp-abc")
        tc.close()

        log_file = tmp_path / "logs" / "run-003.jsonl"
        event = json.loads(log_file.read_text().strip())
        assert event["event"] == "run_start"
        assert event["mission"] == "test-mission"
        assert event["vds_fingerprint"] == "fp-abc"
        assert event["run_id"] == "run-003"

    def test_emit_worker_spawn(self, tmp_path: Path) -> None:
        from src.sdc_b0.telemetry import TelemetryCollector
        tc = TelemetryCollector("run-004", tmp_path / "logs")
        tc.emit_worker_spawn(
            worker_id="w1",
            task_id="t1",
            worktree_path="/tmp/wt-t1",
            base_sha="abc123",
            process_fingerprint="fp-xyz",
        )
        tc.close()

        log_file = tmp_path / "logs" / "run-004.jsonl"
        event = json.loads(log_file.read_text().strip())
        assert event["event"] == "worker_spawn"
        assert event["worker_id"] == "w1"
        assert event["base_sha"] == "abc123"

    def test_emit_worker_command(self, tmp_path: Path) -> None:
        from src.sdc_b0.telemetry import TelemetryCollector
        tc = TelemetryCollector("run-005", tmp_path / "logs")
        tc.emit_worker_command(
            worker_id="w1",
            process_fingerprint="fp-1",
            cmd="echo hello",
            exit_code=0,
            duration_ms=42,
            stdout_bytes=6,
            stderr_bytes=0,
        )
        tc.close()

        log_file = tmp_path / "logs" / "run-005.jsonl"
        event = json.loads(log_file.read_text().strip())
        assert event["event"] == "worker_command"
        assert event["cmd"] == "echo hello"
        assert event["exit_code"] == 0
        assert event["process_fingerprint"] == "fp-1"

    def test_multiple_events_append(self, tmp_path: Path) -> None:
        from src.sdc_b0.telemetry import TelemetryCollector
        tc = TelemetryCollector("run-006", tmp_path / "logs")
        tc.emit("e1", {})
        tc.emit("e2", {})
        tc.emit("e3", {})
        tc.close()

        log_file = tmp_path / "logs" / "run-006.jsonl"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_close_is_idempotent(self, tmp_path: Path) -> None:
        from src.sdc_b0.telemetry import TelemetryCollector
        tc = TelemetryCollector("run-007", tmp_path / "logs")
        tc.emit("e1", {})
        tc.close()
        tc.close()  # Should not raise
