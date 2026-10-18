from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import uuid


class LeaseStatus(str, Enum):
    ACTIVE = "active"
    FENCED = "fenced"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass(slots=True)
class WorkerLease:
    lease_id: str
    node_id: str
    worker_id: str
    authority_grant_id: str
    capabilities: frozenset[str]
    issued_at: datetime
    expires_at: datetime
    heartbeat_at: datetime
    fencing_token: int
    status: LeaseStatus = LeaseStatus.ACTIVE


class LeaseManager:
    """One-current-lease-per-node manager with monotonically increasing fences."""

    def __init__(self) -> None:
        self._leases: dict[str, WorkerLease] = {}
        self._current_by_node: dict[str, str] = {}
        self._fence_by_node: dict[str, int] = {}

    def get(self, lease_id: str) -> WorkerLease:
        try:
            return self._leases[lease_id]
        except KeyError as exc:
            raise KeyError(f"unknown worker lease {lease_id}") from exc

    def issue(
        self,
        *,
        node_id: str,
        worker_id: str,
        authority_grant_id: str,
        capabilities: set[str] | frozenset[str],
        ttl: timedelta,
        now: datetime,
    ) -> WorkerLease:
        if ttl.total_seconds() <= 0:
            raise ValueError("lease ttl must be positive")
        if not node_id.strip() or not worker_id.strip() or not authority_grant_id.strip():
            raise ValueError("node_id, worker_id and authority_grant_id must be non-empty")
        current_id = self._current_by_node.get(node_id)
        if current_id is not None:
            current = self._leases[current_id]
            if current.status is LeaseStatus.ACTIVE:
                current.status = LeaseStatus.FENCED
        token = self._fence_by_node.get(node_id, 0) + 1
        self._fence_by_node[node_id] = token
        lease = WorkerLease(
            lease_id="lease_" + uuid.uuid4().hex[:24],
            node_id=node_id,
            worker_id=worker_id,
            authority_grant_id=authority_grant_id,
            capabilities=frozenset(capabilities),
            issued_at=now,
            expires_at=now + ttl,
            heartbeat_at=now,
            fencing_token=token,
        )
        self._leases[lease.lease_id] = lease
        self._current_by_node[node_id] = lease.lease_id
        return lease

    def _expire_if_needed(self, lease: WorkerLease, now: datetime) -> None:
        if lease.status is LeaseStatus.ACTIVE and now >= lease.expires_at:
            lease.status = LeaseStatus.EXPIRED

    def validate(self, lease_id: str, *, fencing_token: int, now: datetime) -> WorkerLease:
        lease = self.get(lease_id)
        self._expire_if_needed(lease, now)
        if lease.status is LeaseStatus.EXPIRED:
            raise RuntimeError("worker lease expired")
        if lease.status is LeaseStatus.FENCED:
            raise RuntimeError("worker lease fenced by a newer assignment")
        if lease.status is LeaseStatus.REVOKED:
            raise RuntimeError("worker lease revoked")
        if self._current_by_node.get(lease.node_id) != lease_id:
            raise RuntimeError("worker lease is not current for node")
        if fencing_token != lease.fencing_token:
            raise RuntimeError("stale fencing token")
        return lease

    def heartbeat(self, lease_id: str, *, fencing_token: int, now: datetime) -> None:
        lease = self.validate(lease_id, fencing_token=fencing_token, now=now)
        lease.heartbeat_at = now

    def renew(self, lease_id: str, *, fencing_token: int, ttl: timedelta, now: datetime) -> WorkerLease:
        if ttl.total_seconds() <= 0:
            raise ValueError("lease ttl must be positive")
        lease = self.validate(lease_id, fencing_token=fencing_token, now=now)
        lease.expires_at = now + ttl
        lease.heartbeat_at = now
        return lease

    def revoke(self, lease_id: str) -> None:
        lease = self.get(lease_id)
        if lease.status is LeaseStatus.ACTIVE:
            lease.status = LeaseStatus.REVOKED
        if self._current_by_node.get(lease.node_id) == lease_id:
            self._current_by_node.pop(lease.node_id, None)

    def active(self, *, now: datetime) -> tuple[WorkerLease, ...]:
        rows: list[WorkerLease] = []
        for lease in self._leases.values():
            self._expire_if_needed(lease, now)
            if lease.status is LeaseStatus.ACTIVE and self._current_by_node.get(lease.node_id) == lease.lease_id:
                rows.append(lease)
        return tuple(rows)
