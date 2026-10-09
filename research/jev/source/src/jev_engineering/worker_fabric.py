from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class WorkerEndpoint:
    worker_id: str
    habitat_id: str
    endpoint_uri: str
    capabilities: frozenset[str]
    identity_key_id: str
    last_seen: datetime

    def __post_init__(self) -> None:
        for name, value in (
            ("worker_id", self.worker_id),
            ("habitat_id", self.habitat_id),
            ("endpoint_uri", self.endpoint_uri),
            ("identity_key_id", self.identity_key_id),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} must be non-empty")
        if self.last_seen.tzinfo is None or self.last_seen.utcoffset() is None:
            raise ValueError("last_seen must be timezone-aware")


class WorkerDirectory:
    """In-memory worker discovery registry for Aftergraph-native endpoints.

    Registration/discovery is intentionally separate from transport. Endpoint URIs
    such as aftergraph://jonas-lenovo are identifiers here, not proof of a live
    network channel.
    """

    def __init__(self, *, stale_after: timedelta = timedelta(seconds=60)) -> None:
        if stale_after.total_seconds() <= 0:
            raise ValueError("stale_after must be positive")
        self.stale_after = stale_after
        self._workers: dict[str, WorkerEndpoint] = {}

    def register(self, endpoint: WorkerEndpoint) -> None:
        self._workers[endpoint.worker_id] = endpoint

    def heartbeat(self, worker_id: str, *, now: datetime) -> WorkerEndpoint:
        current = self._workers[worker_id]
        endpoint = WorkerEndpoint(
            current.worker_id, current.habitat_id, current.endpoint_uri,
            current.capabilities, current.identity_key_id, now,
        )
        self._workers[worker_id] = endpoint
        return endpoint

    def get(self, worker_id: str) -> WorkerEndpoint:
        try:
            return self._workers[worker_id]
        except KeyError as exc:
            raise KeyError(f"unknown worker {worker_id}") from exc

    def healthy(self, *, now: datetime) -> tuple[WorkerEndpoint, ...]:
        return tuple(
            worker for worker in self._workers.values()
            if now - worker.last_seen <= self.stale_after
        )

    def select(self, *, required_capabilities: set[str] | frozenset[str], now: datetime) -> WorkerEndpoint:
        required = frozenset(required_capabilities)
        eligible = [
            worker for worker in self.healthy(now=now)
            if required.issubset(worker.capabilities)
        ]
        if not eligible:
            raise RuntimeError("no healthy worker satisfies required capabilities")
        return sorted(eligible, key=lambda w: (len(w.capabilities), w.worker_id))[0]
