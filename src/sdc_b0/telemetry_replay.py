"""SDC-B0 Task #56: VDS Execution Telemetry Replay.

Protocol source: docs/sdc/b0/2026-09-09-vds-execution-telemetry-schema.md

Replays JSONL telemetry logs to reconstruct execution timelines, validate
lifecycle completeness, detect gaps, and produce replay summaries.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_LIFECYCLE_EVENTS = frozenset({
    "run_start",
    "worker_spawn",
    "worker_command",
})


class TelemetryReplayer:
    """Loads and replays SDC-B0 telemetry JSONL logs."""

    def __init__(self, log_dir: str | Path) -> None:
        self.log_dir = Path(log_dir)

    def load(self) -> list[dict[str, Any]]:
        """Load all JSONL events from the log directory, sorted by timestamp."""
        events: list[dict[str, Any]] = []
        if not self.log_dir.exists():
            return events
        for path in sorted(self.log_dir.glob("*.jsonl")):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return self._sort_by_time(events)

    def _sort_by_time(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort events by their timestamp field."""
        def _ts(e: dict[str, Any]) -> str:
            for key in ("timestamp", "started_at", "executed_at", "ended_at",
                        "spawned_at", "submitted_at", "completed_at",
                        "refreshed_at", "replanned_at", "detected_at",
                        "merged_at", "rebased_at", "snapshot_at"):
                if key in e:
                    return str(e[key])
            return ""
        return sorted(events, key=_ts)

    def validate(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Validate that required lifecycle events exist."""
        found_types: set[str] = set()
        for e in events:
            if isinstance(e, dict):
                ev = e.get("event")
                if isinstance(ev, str):
                    found_types.add(ev)
        missing = REQUIRED_LIFECYCLE_EVENTS - found_types
        return {
            "valid": len(missing) == 0,
            "missing_events": sorted(missing),
            "total_events": len(events),
            "event_types_found": sorted(found_types),
        }

    def detect_gaps(
        self,
        events: list[dict[str, Any]],
        threshold_seconds: float = 300.0,
    ) -> list[dict[str, Any]]:
        """Detect temporal gaps between consecutive events exceeding threshold."""
        gaps: list[dict[str, Any]] = []
        if len(events) < 2:
            return gaps

        sorted_events = self._sort_by_time(events)

        def _parse_ts(e: dict[str, Any]) -> datetime | None:
            for key in ("timestamp", "started_at", "executed_at", "ended_at",
                        "spawned_at", "submitted_at", "completed_at"):
                val = e.get(key)
                if val:
                    try:
                        s = str(val).replace("Z", "+00:00")
                        return datetime.fromisoformat(s)
                    except (ValueError, TypeError):
                        continue
            return None

        prev_dt: datetime | None = None
        prev_event: dict[str, Any] | None = None
        for ev in sorted_events:
            dt = _parse_ts(ev)
            if dt is None:
                continue
            if prev_dt is not None:
                delta = (dt - prev_dt).total_seconds()
                if delta > threshold_seconds:
                    gaps.append({
                        "gap_seconds": delta,
                        "after_event": prev_event.get("event") if prev_event else None,
                        "before_event": ev.get("event"),
                        "threshold_seconds": threshold_seconds,
                    })
            prev_dt = dt
            prev_event = ev
        return gaps

    def summarize(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Produce a replay summary dict."""
        validation = self.validate(events)
        gaps = self.detect_gaps(events)
        event_counts: dict[str, int] = {}
        for e in events:
            t = e.get("event", "unknown")
            event_counts[t] = event_counts.get(t, 0) + 1

        run_ids: set[str] = set()
        worker_ids: set[str] = set()
        for e in events:
            rid = e.get("run_id") if isinstance(e, dict) else None
            wid = e.get("worker_id") if isinstance(e, dict) else None
            if isinstance(rid, str):
                run_ids.add(rid)
            if isinstance(wid, str):
                worker_ids.add(wid)

        return {
            "total_events": len(events),
            "validation": validation,
            "gaps_detected": len(gaps),
            "gaps": gaps,
            "event_counts": event_counts,
            "unique_run_ids": sorted(run_ids),
            "unique_worker_ids": sorted(worker_ids),
            "replay_complete": validation["valid"] and len(gaps) == 0,
        }
