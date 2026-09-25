from __future__ import annotations

from datetime import datetime, timedelta

from .authority import AuthorityLedger
from .mission_graph import MissionGraph, NodeState
from .worker_leases import LeaseManager, WorkerLease


class DistributedMissionRuntime:
    """Lease-fenced dispatcher for independent/speculative MissionGraph branches."""

    def __init__(
        self,
        graph: MissionGraph,
        leases: LeaseManager,
        authority: AuthorityLedger,
        *,
        max_parallel_workers: int = 4,
    ) -> None:
        if max_parallel_workers < 1:
            raise ValueError("max_parallel_workers must be >= 1")
        self.graph = graph
        self.leases = leases
        self.authority = authority
        self.max_parallel_workers = max_parallel_workers

    def active_count(self, *, now: datetime) -> int:
        return len(self.leases.active(now=now))

    def _required_capabilities(self, node_id: str) -> frozenset[str]:
        raw = self.graph.nodes[node_id].metadata.get("required_capabilities", [])
        if not isinstance(raw, (list, tuple, set, frozenset)):
            raise ValueError("required_capabilities metadata must be a collection")
        return frozenset(str(v) for v in raw)

    def _authority_scope(self, node_id: str) -> str:
        value = self.graph.nodes[node_id].metadata.get("authority_scope", "mission.execute")
        if not isinstance(value, str) or not value:
            raise ValueError("authority_scope metadata must be a non-empty string")
        return value

    def dispatch(
        self,
        node_id: str,
        *,
        worker_id: str,
        authority_grant_id: str,
        capabilities: set[str] | frozenset[str],
        ttl: timedelta,
        now: datetime,
    ) -> WorkerLease:
        if self.active_count(now=now) >= self.max_parallel_workers:
            raise RuntimeError("parallelism limit reached")
        node = self.graph.nodes[node_id]
        self.authority.authorize(authority_grant_id, scope=self._authority_scope(node_id), amount_usd=0, now=now)
        offered = frozenset(capabilities)
        required = self._required_capabilities(node_id)
        if not required.issubset(offered):
            raise RuntimeError("worker lacks required capabilities")
        if node.state is NodeState.BLOCKED:
            candidates = {n.node_id for n in self.graph.speculative_candidates()}
            if node_id not in candidates:
                raise RuntimeError("node is blocked and not speculation-eligible")
            self.graph.begin_speculation(node_id)
        elif node.state is not NodeState.READY:
            raise RuntimeError(f"node state {node.state.value!r} is not dispatchable")
        return self.leases.issue(
            node_id=node_id,
            worker_id=worker_id,
            authority_grant_id=authority_grant_id,
            capabilities=offered,
            ttl=ttl,
            now=now,
        )

    def reassign(
        self,
        node_id: str,
        *,
        worker_id: str,
        authority_grant_id: str,
        capabilities: set[str] | frozenset[str],
        ttl: timedelta,
        now: datetime,
    ) -> WorkerLease:
        node = self.graph.nodes[node_id]
        if node.state not in {NodeState.READY, NodeState.SPECULATING}:
            raise RuntimeError("only active work nodes can be reassigned")
        self.authority.authorize(authority_grant_id, scope=self._authority_scope(node_id), amount_usd=0, now=now)
        required = self._required_capabilities(node_id)
        offered = frozenset(capabilities)
        if not required.issubset(offered):
            raise RuntimeError("worker lacks required capabilities")
        return self.leases.issue(
            node_id=node_id,
            worker_id=worker_id,
            authority_grant_id=authority_grant_id,
            capabilities=offered,
            ttl=ttl,
            now=now,
        )

    def mark_verified(self, node_id: str, lease_id: str, fencing_token: int, *, now: datetime) -> None:
        lease = self.leases.validate(lease_id, fencing_token=fencing_token, now=now)
        if lease.node_id != node_id:
            raise RuntimeError("lease is bound to a different node")
        self.authority.authorize(lease.authority_grant_id, scope=self._authority_scope(node_id), amount_usd=0, now=now)
        self.graph.mark_verified(node_id)

    def commit(self, node_id: str, lease_id: str, fencing_token: int, *, now: datetime) -> None:
        lease = self.leases.validate(lease_id, fencing_token=fencing_token, now=now)
        if lease.node_id != node_id:
            raise RuntimeError("lease is bound to a different node")
        self.authority.authorize(lease.authority_grant_id, scope=self._authority_scope(node_id), amount_usd=0, now=now)
        self.graph.commit(node_id)
        self.leases.revoke(lease_id)

    def fail(self, node_id: str, lease_id: str, fencing_token: int, *, now: datetime) -> None:
        lease = self.leases.validate(lease_id, fencing_token=fencing_token, now=now)
        if lease.node_id != node_id:
            raise RuntimeError("lease is bound to a different node")
        self.graph.fail(node_id)
        self.leases.revoke(lease_id)
