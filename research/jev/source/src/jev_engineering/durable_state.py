from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import uuid

from .worker_leases import LeaseStatus, WorkerLease


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _ts(value: datetime) -> float:
    _aware(value, "datetime")
    return value.astimezone(timezone.utc).timestamp()


def _dt(value: float) -> datetime:
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


class SqliteLeaseStore:
    """Durable reference lease store with transactional fencing.

    SQLite provides a crash-durable single-database reference. Multi-host deployments
    should replace this interface with a consensus/transactional store; shared network
    filesystems are not assumed to provide distributed consensus.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        con = self._connect()
        try:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS leases (
              lease_id TEXT PRIMARY KEY,
              node_id TEXT NOT NULL,
              worker_id TEXT NOT NULL,
              authority_grant_id TEXT NOT NULL,
              capabilities_json TEXT NOT NULL,
              issued_at REAL NOT NULL,
              expires_at REAL NOT NULL,
              heartbeat_at REAL NOT NULL,
              fencing_token INTEGER NOT NULL,
              status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS node_fences (
              node_id TEXT PRIMARY KEY,
              current_lease_id TEXT,
              fencing_token INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_leases_node ON leases(node_id);
            """)
        finally:
            con.close()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
        return con

    @staticmethod
    def _row(row: sqlite3.Row) -> WorkerLease:
        return WorkerLease(
            lease_id=row["lease_id"], node_id=row["node_id"], worker_id=row["worker_id"],
            authority_grant_id=row["authority_grant_id"],
            capabilities=frozenset(json.loads(row["capabilities_json"])),
            issued_at=_dt(row["issued_at"]), expires_at=_dt(row["expires_at"]),
            heartbeat_at=_dt(row["heartbeat_at"]), fencing_token=int(row["fencing_token"]),
            status=LeaseStatus(row["status"]),
        )

    def get(self, lease_id: str) -> WorkerLease:
        con = self._connect()
        try:
            row = con.execute("SELECT * FROM leases WHERE lease_id=?", (lease_id,)).fetchone()
        finally:
            con.close()
        if row is None:
            raise KeyError(f"unknown worker lease {lease_id}")
        return self._row(row)

    def issue(self, *, node_id: str, worker_id: str, authority_grant_id: str, capabilities, ttl: timedelta, now: datetime) -> WorkerLease:
        _aware(now, "now")
        if ttl.total_seconds() <= 0:
            raise ValueError("lease ttl must be positive")
        lease_id = "lease_" + uuid.uuid4().hex[:24]
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT current_lease_id, fencing_token FROM node_fences WHERE node_id=?", (node_id,)).fetchone()
            token = (int(row["fencing_token"]) if row else 0) + 1
            if row and row["current_lease_id"]:
                con.execute("UPDATE leases SET status=? WHERE lease_id=? AND status=?", (LeaseStatus.FENCED.value, row["current_lease_id"], LeaseStatus.ACTIVE.value))
            con.execute(
                "INSERT INTO leases VALUES (?,?,?,?,?,?,?,?,?,?)",
                (lease_id, node_id, worker_id, authority_grant_id, json.dumps(sorted(set(capabilities))), _ts(now), _ts(now + ttl), _ts(now), token, LeaseStatus.ACTIVE.value),
            )
            con.execute(
                "INSERT INTO node_fences(node_id,current_lease_id,fencing_token) VALUES(?,?,?) ON CONFLICT(node_id) DO UPDATE SET current_lease_id=excluded.current_lease_id,fencing_token=excluded.fencing_token",
                (node_id, lease_id, token),
            )
            con.execute("COMMIT")
        finally:
            con.close()
        return self.get(lease_id)

    def validate(self, lease_id: str, *, fencing_token: int, now: datetime) -> WorkerLease:
        _aware(now, "now")
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM leases WHERE lease_id=?", (lease_id,)).fetchone()
            if row is None:
                con.execute("ROLLBACK")
                raise KeyError(f"unknown worker lease {lease_id}")
            lease = self._row(row)
            if lease.status is LeaseStatus.ACTIVE and now >= lease.expires_at:
                con.execute("UPDATE leases SET status=? WHERE lease_id=?", (LeaseStatus.EXPIRED.value, lease_id))
                con.execute("COMMIT")
                raise RuntimeError("worker lease expired")
            current = con.execute("SELECT current_lease_id,fencing_token FROM node_fences WHERE node_id=?", (lease.node_id,)).fetchone()
            con.execute("COMMIT")
        finally:
            con.close()
        if lease.status is LeaseStatus.FENCED:
            raise RuntimeError("worker lease fenced by a newer assignment")
        if lease.status is LeaseStatus.REVOKED:
            raise RuntimeError("worker lease revoked")
        if lease.status is LeaseStatus.EXPIRED:
            raise RuntimeError("worker lease expired")
        if current is None or current["current_lease_id"] != lease_id:
            raise RuntimeError("worker lease is not current for node")
        if int(current["fencing_token"]) != fencing_token or lease.fencing_token != fencing_token:
            raise RuntimeError("stale fencing token")
        return lease

    def heartbeat(self, lease_id: str, *, fencing_token: int, now: datetime) -> None:
        self.validate(lease_id, fencing_token=fencing_token, now=now)
        con = self._connect()
        try:
            con.execute("UPDATE leases SET heartbeat_at=? WHERE lease_id=?", (_ts(now), lease_id))
        finally:
            con.close()

    def renew(self, lease_id: str, *, fencing_token: int, ttl: timedelta, now: datetime) -> WorkerLease:
        if ttl.total_seconds() <= 0:
            raise ValueError("lease ttl must be positive")
        self.validate(lease_id, fencing_token=fencing_token, now=now)
        con = self._connect()
        try:
            con.execute("UPDATE leases SET heartbeat_at=?, expires_at=? WHERE lease_id=?", (_ts(now), _ts(now + ttl), lease_id))
        finally:
            con.close()
        return self.get(lease_id)

    def revoke(self, lease_id: str) -> None:
        lease = self.get(lease_id)
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("UPDATE leases SET status=? WHERE lease_id=? AND status=?", (LeaseStatus.REVOKED.value, lease_id, LeaseStatus.ACTIVE.value))
            con.execute("UPDATE node_fences SET current_lease_id=NULL WHERE node_id=? AND current_lease_id=?", (lease.node_id, lease_id))
            con.execute("COMMIT")
        finally:
            con.close()

    def active(self, *, now: datetime) -> tuple[WorkerLease, ...]:
        _aware(now, "now")
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("UPDATE leases SET status=? WHERE status=? AND expires_at<=?", (LeaseStatus.EXPIRED.value, LeaseStatus.ACTIVE.value, _ts(now)))
            rows = con.execute("SELECT l.* FROM leases l JOIN node_fences f ON f.current_lease_id=l.lease_id WHERE l.status=?", (LeaseStatus.ACTIVE.value,)).fetchall()
            con.execute("COMMIT")
        finally:
            con.close()
        return tuple(self._row(row) for row in rows)
