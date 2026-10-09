from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from jev_engineering.worker_leases import LeaseManager, LeaseStatus


def _now() -> datetime:
    return datetime(2026, 9, 25, 1, 0, tzinfo=timezone.utc)


def test_reassignment_fences_stale_worker() -> None:
    now = _now()
    leases = LeaseManager()
    first = leases.issue(
        node_id="n1", worker_id="worker:a", authority_grant_id="grant:1",
        capabilities={"python"}, ttl=timedelta(minutes=10), now=now,
    )
    second = leases.issue(
        node_id="n1", worker_id="worker:b", authority_grant_id="grant:1",
        capabilities={"python"}, ttl=timedelta(minutes=10), now=now + timedelta(seconds=1),
    )
    assert second.fencing_token > first.fencing_token
    assert leases.get(first.lease_id).status is LeaseStatus.FENCED
    with pytest.raises(RuntimeError, match="fenced|current"):
        leases.validate(first.lease_id, fencing_token=first.fencing_token, now=now + timedelta(seconds=2))
    assert leases.validate(second.lease_id, fencing_token=second.fencing_token, now=now + timedelta(seconds=2)).worker_id == "worker:b"


def test_lease_expiry_and_heartbeat_are_fail_closed() -> None:
    now = _now()
    leases = LeaseManager()
    lease = leases.issue(
        node_id="n", worker_id="w", authority_grant_id="g", capabilities=set(),
        ttl=timedelta(seconds=5), now=now,
    )
    leases.heartbeat(lease.lease_id, fencing_token=lease.fencing_token, now=now + timedelta(seconds=2))
    assert leases.get(lease.lease_id).heartbeat_at == now + timedelta(seconds=2)
    with pytest.raises(RuntimeError, match="expired"):
        leases.validate(lease.lease_id, fencing_token=lease.fencing_token, now=now + timedelta(seconds=6))
