"""SDC-B0 Task #60: Telemetry Collector.

Protocol source: docs/sdc/b0/2026-09-09-vds-execution-telemetry-schema.md

Collects and persists SDC-B0 telemetry events with write-ahead durability.
All events are synchronously flushed to survive worker crashes.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


class TelemetryCollector:
    """Collects and persists SDC-B0 telemetry events.

    Events are written ahead to a JSONL log file with synchronous flush.
    The collector survives worker crashes via write-ahead durability.
    """

    def __init__(self, run_id: str, log_dir: Path) -> None:
        self._run_id = run_id
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._log_dir / f"{run_id}.jsonl"
        self._file: TextIO | None = open(self._log_path, "a")  # noqa: SIM115

    def _timestamp(self) -> str:
        """ISO8601 UTC timestamp with microsecond precision."""
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit a telemetry event with write-ahead durability."""
        if self._file is None:
            raise RuntimeError("TelemetryCollector is closed")
        event = {"event": event_type, "timestamp": self._timestamp(), **payload}
        line = json.dumps(event, separators=(",", ":")) + "\n"
        self._file.write(line)
        self._file.flush()

    def emit_run_start(self, mission: str, vds_fingerprint: str) -> None:
        """Emit run_start lifecycle event."""
        self.emit("run_start", {
            "run_id": self._run_id,
            "mission": mission,
            "vds_fingerprint": vds_fingerprint,
            "started_at": self._timestamp(),
        })

    def emit_worker_spawn(
        self,
        worker_id: str,
        task_id: str,
        worktree_path: str,
        base_sha: str,
        process_fingerprint: str,
    ) -> None:
        """Emit worker_spawn event."""
        self.emit("worker_spawn", {
            "worker_id": worker_id,
            "task_id": task_id,
            "worktree_path": worktree_path,
            "base_sha": base_sha,
            "process_fingerprint": process_fingerprint,
            "spawned_at": self._timestamp(),
        })

    def emit_worker_command(
        self,
        worker_id: str,
        process_fingerprint: str,
        cmd: str,
        exit_code: int,
        duration_ms: int,
        stdout_bytes: int,
        stderr_bytes: int,
    ) -> None:
        """Emit worker_command event."""
        self.emit("worker_command", {
            "worker_id": worker_id,
            "process_fingerprint": process_fingerprint,
            "cmd": cmd,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "stdout_bytes": stdout_bytes,
            "stderr_bytes": stderr_bytes,
            "executed_at": self._timestamp(),
        })

    def close(self) -> None:
        """Flush and close the telemetry log. Idempotent."""
        if self._file is not None:
            try:
                self._file.flush()
                self._file.close()
            except (ValueError, OSError):
                pass
            self._file = None
