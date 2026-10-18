from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from jev_engineering.durable_state import SqliteLeaseStore
from jev_engineering.worker_leases import LeaseStatus


def test_sqlite_lease_store_persists_and_fences_across_instances(tmp_path) -> None:
    db = tmp_path / "fabric.db"
    now = datetime(2026, 9, 25, 2, 0, tzinfo=timezone.utc)
    a = SqliteLeaseStore(db)
    first = a.issue(node_id="n1", worker_id="w1", authority_grant_id="g1", capabilities={"python"}, ttl=timedelta(minutes=5), now=now)
    b = SqliteLeaseStore(db)
    assert b.validate(first.lease_id, fencing_token=first.fencing_token, now=now).worker_id == "w1"
    second = b.issue(node_id="n1", worker_id="w2", authority_grant_id="g1", capabilities={"python"}, ttl=timedelta(minutes=5), now=now + timedelta(seconds=1))
    assert second.fencing_token == first.fencing_token + 1
    assert a.get(first.lease_id).status is LeaseStatus.FENCED
    with pytest.raises(RuntimeError, match="fenced|current|stale"):
        a.validate(first.lease_id, fencing_token=first.fencing_token, now=now + timedelta(seconds=2))
