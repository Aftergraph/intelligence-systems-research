from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jev_engineering.worker_fabric import WorkerDirectory, WorkerEndpoint


def test_worker_directory_selects_healthy_capability_match_and_expires_stale() -> None:
    now = datetime(2026, 9, 25, 2, 0, tzinfo=timezone.utc)
    d = WorkerDirectory(stale_after=timedelta(seconds=30))
    d.register(WorkerEndpoint("lenovo", "habitat:lenovo", "aftergraph://jonas-lenovo", frozenset({"python", "browser"}), "wid-lenovo", now))
    d.register(WorkerEndpoint("vds", "habitat:vds", "aftergraph://vds", frozenset({"python"}), "wid-vds", now))
    assert d.select(required_capabilities={"browser"}, now=now).worker_id == "lenovo"
    d.heartbeat("vds", now=now + timedelta(seconds=20))
    healthy = {w.worker_id for w in d.healthy(now=now + timedelta(seconds=31))}
    assert healthy == {"vds"}
