"""SDC-B0 Task #56: Tests for TelemetryReplayer.

Protocol source: docs/sdc/b0/2026-09-09-vds-execution-telemetry-schema.md
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.sdc_b0.telemetry_replay import TelemetryReplayer, REQUIRED_LIFECYCLE_EVENTS


@pytest.fixture
def log_dir(tmp_path: Path) -> Path:
    return tmp_path / "logs"


@pytest.fixture
def replayer(log_dir: Path) -> TelemetryReplayer:
    log_dir.mkdir(parents=True, exist_ok=True)
    return TelemetryReplayer(log_dir)


def _write_events(log_dir: Path, events: list[dict], filename: str = "events.jsonl") -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / filename, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


class TestLoad:
    def test_load_empty_dir(self, replayer: TelemetryReplayer) -> None:
        assert replayer.load() == []

    def test_load_nonexistent_dir(self, tmp_path: Path) -> None:
        r = TelemetryReplayer(tmp_path / "nonexistent")
        assert r.load() == []

    def test_load_single_file(self, replayer: TelemetryReplayer, log_dir: Path) -> None:
        events = [
            {"event": "run_start", "run_id": "r1", "started_at": "2026-09-10T00:00:00Z"},
            {"event": "worker_spawn", "worker_id": "w1", "spawned_at": "2026-09-10T00:00:01Z"},
        ]
        _write_events(log_dir, events)
        loaded = replayer.load()
        assert len(loaded) == 2
        assert loaded[0]["event"] == "run_start"

    def test_load_multiple_files_sorted(self, replayer: TelemetryReplayer, log_dir: Path) -> None:
        _write_events(log_dir, [{"event": "worker_command", "executed_at": "2026-09-10T00:00:05Z"}], "b.jsonl")
        _write_events(log_dir, [{"event": "run_start", "started_at": "2026-09-10T00:00:00Z"}], "a.jsonl")
        loaded = replayer.load()
        assert len(loaded) == 2
        assert loaded[0]["event"] == "run_start"
        assert loaded[1]["event"] == "worker_command"

    def test_load_skips_malformed_lines(self, replayer: TelemetryReplayer, log_dir: Path) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "events.jsonl", "w") as f:
            f.write('{"event": "run_start", "started_at": "2026-09-10T00:00:00Z"}\n')
            f.write("not valid json\n")
            f.write('{"event": "worker_spawn", "spawned_at": "2026-09-10T00:00:01Z"}\n')
        loaded = replayer.load()
        assert len(loaded) == 2


class TestValidate:
    def test_validate_all_required_present(self, replayer: TelemetryReplayer) -> None:
        events = [
            {"event": "run_start", "started_at": "2026-09-10T00:00:00Z"},
            {"event": "worker_spawn", "spawned_at": "2026-09-10T00:00:01Z"},
            {"event": "worker_command", "executed_at": "2026-09-10T00:00:02Z"},
        ]
        result = replayer.validate(events)
        assert result["valid"] is True
        assert result["missing_events"] == []
        assert result["total_events"] == 3

    def test_validate_missing_worker_spawn(self, replayer: TelemetryReplayer) -> None:
        events = [
            {"event": "run_start", "started_at": "2026-09-10T00:00:00Z"},
            {"event": "worker_command", "executed_at": "2026-09-10T00:00:02Z"},
        ]
        result = replayer.validate(events)
        assert result["valid"] is False
        assert "worker_spawn" in result["missing_events"]

    def test_validate_empty_events(self, replayer: TelemetryReplayer) -> None:
        result = replayer.validate([])
        assert result["valid"] is False
        assert sorted(result["missing_events"]) == sorted(REQUIRED_LIFECYCLE_EVENTS)

    def test_validate_event_types_found(self, replayer: TelemetryReplayer) -> None:
        events = [
            {"event": "run_start"},
            {"event": "worker_spawn"},
            {"event": "worker_command"},
            {"event": "git_merge"},
        ]
        result = replayer.validate(events)
        assert "git_merge" in result["event_types_found"]
        assert "run_start" in result["event_types_found"]


class TestDetectGaps:
    def test_no_gaps_under_threshold(self, replayer: TelemetryReplayer) -> None:
        events = [
            {"event": "run_start", "started_at": "2026-09-10T00:00:00Z"},
            {"event": "worker_spawn", "spawned_at": "2026-09-10T00:01:00Z"},
            {"event": "worker_command", "executed_at": "2026-09-10T00:02:00Z"},
        ]
        gaps = replayer.detect_gaps(events, threshold_seconds=300.0)
        assert len(gaps) == 0

    def test_gap_detected_over_threshold(self, replayer: TelemetryReplayer) -> None:
        events = [
            {"event": "run_start", "started_at": "2026-09-10T00:00:00Z"},
            {"event": "worker_spawn", "spawned_at": "2026-09-10T00:10:00Z"},
        ]
        gaps = replayer.detect_gaps(events, threshold_seconds=300.0)
        assert len(gaps) == 1
        assert gaps[0]["gap_seconds"] == 600.0
        assert gaps[0]["after_event"] == "run_start"
        assert gaps[0]["before_event"] == "worker_spawn"

    def test_single_event_no_gaps(self, replayer: TelemetryReplayer) -> None:
        events = [{"event": "run_start", "started_at": "2026-09-10T00:00:00Z"}]
        assert replayer.detect_gaps(events) == []

    def test_empty_events_no_gaps(self, replayer: TelemetryReplayer) -> None:
        assert replayer.detect_gaps([]) == []

    def test_events_without_timestamps_skipped(self, replayer: TelemetryReplayer) -> None:
        events = [
            {"event": "run_start", "started_at": "2026-09-10T00:00:00Z"},
            {"event": "unknown_event"},
            {"event": "worker_spawn", "spawned_at": "2026-09-10T00:10:00Z"},
        ]
        gaps = replayer.detect_gaps(events, threshold_seconds=300.0)
        assert len(gaps) == 1


class TestSummarize:
    def test_summarize_complete_run(self, replayer: TelemetryReplayer) -> None:
        events = [
            {"event": "run_start", "run_id": "r1", "started_at": "2026-09-10T00:00:00Z"},
            {"event": "worker_spawn", "worker_id": "w1", "spawned_at": "2026-09-10T00:00:01Z"},
            {"event": "worker_command", "worker_id": "w1", "executed_at": "2026-09-10T00:00:02Z"},
        ]
        summary = replayer.summarize(events)
        assert summary["total_events"] == 3
        assert summary["validation"]["valid"] is True
        assert summary["gaps_detected"] == 0
        assert summary["replay_complete"] is True
        assert "r1" in summary["unique_run_ids"]
        assert "w1" in summary["unique_worker_ids"]

    def test_summarize_incomplete_run(self, replayer: TelemetryReplayer) -> None:
        events = [
            {"event": "run_start", "run_id": "r1", "started_at": "2026-09-10T00:00:00Z"},
        ]
        summary = replayer.summarize(events)
        assert summary["replay_complete"] is False
        assert summary["validation"]["valid"] is False

    def test_summarize_event_counts(self, replayer: TelemetryReplayer) -> None:
        events = [
            {"event": "run_start"},
            {"event": "worker_spawn"},
            {"event": "worker_spawn"},
            {"event": "worker_command"},
        ]
        summary = replayer.summarize(events)
        assert summary["event_counts"]["worker_spawn"] == 2
        assert summary["event_counts"]["run_start"] == 1
