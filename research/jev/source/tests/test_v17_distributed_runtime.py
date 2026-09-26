from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from jev_engineering.authority import AuthorityLedger
from jev_engineering.distributed_runtime import DistributedMissionRuntime
from jev_engineering.mission_graph import MissionGraph, MissionNode, NodeState
from jev_engineering.worker_leases import LeaseManager


def _now() -> datetime:
    return datetime(2026, 9, 25, 1, 0, tzinfo=timezone.utc)


def _runtime(max_parallel: int = 2):
    now = _now()
    auth = AuthorityLedger()
    root = auth.issue_root(
        authority_ref="human:jonas", principal="steward",
        scopes={"mission.execute"}, budget_usd=10,
        expires_at=now + timedelta(hours=1), delegation_depth=1,
    )
    graph = MissionGraph([
        MissionNode("a", metadata={"required_capabilities": ["python"]}),
        MissionNode("b", metadata={"required_capabilities": ["python"]}),
        MissionNode("join", dependencies=("a", "b"), speculative_allowed=True, metadata={"required_capabilities": ["python"]}),
    ])
    return now, root, DistributedMissionRuntime(graph, LeaseManager(), auth, max_parallel_workers=max_parallel)


def test_independent_branches_dispatch_in_parallel_and_join_cannot_commit_early() -> None:
    now, root, runtime = _runtime()
    a = runtime.dispatch("a", worker_id="wa", authority_grant_id=root.grant_id, capabilities={"python"}, ttl=timedelta(minutes=5), now=now)
    b = runtime.dispatch("b", worker_id="wb", authority_grant_id=root.grant_id, capabilities={"python"}, ttl=timedelta(minutes=5), now=now)
    assert runtime.active_count(now=now) == 2
    with pytest.raises(RuntimeError, match="parallelism"):
        runtime.dispatch("join", worker_id="wj", authority_grant_id=root.grant_id, capabilities={"python"}, ttl=timedelta(minutes=5), now=now)

    runtime.mark_verified("a", a.lease_id, a.fencing_token, now=now)
    runtime.commit("a", a.lease_id, a.fencing_token, now=now)
    join = runtime.dispatch("join", worker_id="wj", authority_grant_id=root.grant_id, capabilities={"python"}, ttl=timedelta(minutes=5), now=now)
    assert runtime.graph.nodes["join"].state is NodeState.SPECULATING
    with pytest.raises(RuntimeError, match="dependencies"):
        runtime.mark_verified("join", join.lease_id, join.fencing_token, now=now)

    runtime.mark_verified("b", b.lease_id, b.fencing_token, now=now)
    runtime.commit("b", b.lease_id, b.fencing_token, now=now)
    runtime.mark_verified("join", join.lease_id, join.fencing_token, now=now)
    runtime.commit("join", join.lease_id, join.fencing_token, now=now)
    assert runtime.graph.nodes["join"].state is NodeState.COMMITTED


def test_stale_worker_cannot_finish_after_reassignment() -> None:
    now, root, runtime = _runtime(max_parallel=2)
    old = runtime.dispatch("a", worker_id="old", authority_grant_id=root.grant_id, capabilities={"python"}, ttl=timedelta(minutes=5), now=now)
    new = runtime.reassign("a", worker_id="new", authority_grant_id=root.grant_id, capabilities={"python"}, ttl=timedelta(minutes=5), now=now + timedelta(seconds=1))
    with pytest.raises(RuntimeError):
        runtime.mark_verified("a", old.lease_id, old.fencing_token, now=now + timedelta(seconds=2))
    runtime.mark_verified("a", new.lease_id, new.fencing_token, now=now + timedelta(seconds=2))
