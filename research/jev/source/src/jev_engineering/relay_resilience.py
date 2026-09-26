from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from .execution_journal import ExecutionEvent


class RelayGenerationStore:
    """Crash-durable monotonic relay session generations.

    The store is intentionally tiny: one monotonically increasing generation per
    node identity. A restarted relay hub can therefore fence a pre-restart worker
    session instead of accidentally reusing generation 1.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS relay_generations ("
                "node_id TEXT PRIMARY KEY, generation INTEGER NOT NULL CHECK(generation >= 0))"
            )

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
        return con

    def current_generation(self, node_id: str) -> int:
        if not node_id.strip():
            raise ValueError("node_id must be non-empty")
        with self._connect() as con:
            row = con.execute(
                "SELECT generation FROM relay_generations WHERE node_id=?", (node_id,)
            ).fetchone()
        return int(row["generation"]) if row else 0

    def next_generation(self, node_id: str) -> int:
        if not node_id.strip():
            raise ValueError("node_id must be non-empty")
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT generation FROM relay_generations WHERE node_id=?", (node_id,)
            ).fetchone()
            generation = (int(row["generation"]) if row else 0) + 1
            con.execute(
                "INSERT INTO relay_generations(node_id,generation) VALUES(?,?) "
                "ON CONFLICT(node_id) DO UPDATE SET generation=excluded.generation",
                (node_id, generation),
            )
            con.execute("COMMIT")
            return generation
        except Exception:
            try:
                con.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            con.close()


@dataclass(frozen=True, slots=True)
class JournalCheckpoint:
    worker_id: str
    stream_id: str
    cursor: int
    last_event_sha256: str
    complete: bool


class JournalCheckpointStore:
    """Durable client-side journal continuation state.

    Checkpoints contain only the cursor and last independently verified event
    hash. They are not evidence by themselves; they prevent silent replay,
    rollback, or duplicate ingestion after relay reconnects and process restarts.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS journal_checkpoints ("
                "worker_id TEXT NOT NULL, stream_id TEXT NOT NULL, cursor INTEGER NOT NULL, "
                "last_event_sha256 TEXT NOT NULL, complete INTEGER NOT NULL, "
                "PRIMARY KEY(worker_id,stream_id))"
            )

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
        return con

    def get(self, worker_id: str, stream_id: str) -> JournalCheckpoint:
        if not worker_id.strip() or not stream_id.strip():
            raise ValueError("worker_id and stream_id must be non-empty")
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM journal_checkpoints WHERE worker_id=? AND stream_id=?",
                (worker_id, stream_id),
            ).fetchone()
        if row is None:
            return JournalCheckpoint(worker_id, stream_id, 0, "", False)
        return JournalCheckpoint(
            worker_id=str(row["worker_id"]), stream_id=str(row["stream_id"]),
            cursor=int(row["cursor"]), last_event_sha256=str(row["last_event_sha256"]),
            complete=bool(row["complete"]),
        )

    def put(self, checkpoint: JournalCheckpoint) -> None:
        if checkpoint.cursor < 0:
            raise ValueError("journal cursor cannot be negative")
        with self._connect() as con:
            con.execute(
                "INSERT INTO journal_checkpoints(worker_id,stream_id,cursor,last_event_sha256,complete) "
                "VALUES(?,?,?,?,?) ON CONFLICT(worker_id,stream_id) DO UPDATE SET "
                "cursor=excluded.cursor,last_event_sha256=excluded.last_event_sha256,complete=excluded.complete",
                (
                    checkpoint.worker_id, checkpoint.stream_id, checkpoint.cursor,
                    checkpoint.last_event_sha256, 1 if checkpoint.complete else 0,
                ),
            )


def _event_from_mapping(row: Mapping[str, Any]) -> ExecutionEvent:
    return ExecutionEvent(
        sequence=int(row["sequence"]), kind=str(row["kind"]),
        payload=dict(row.get("payload") or {}), observed_at=str(row["observed_at"]),
        previous_sha256=str(row.get("previous_sha256") or ""),
        event_sha256=str(row["event_sha256"]),
    )


def _validate_incremental_events(
    rows: list[Mapping[str, Any]], *, cursor: int, previous_sha256: str
) -> str:
    expected_sequence = cursor
    expected_previous = previous_sha256
    terminal = previous_sha256
    for row in rows:
        event = _event_from_mapping(row)
        if event.sequence != expected_sequence:
            raise RuntimeError("journal event sequence discontinuity")
        if event.previous_sha256 != expected_previous:
            raise RuntimeError("journal event previous hash mismatch")
        # Re-mint with the original observed_at to verify the canonical digest.
        checked = ExecutionEvent.mint(
            sequence=event.sequence, kind=event.kind, payload=event.payload,
            previous_sha256=event.previous_sha256, observed_at=event.observed_at,
        )
        if checked.event_sha256 != event.event_sha256:
            raise RuntimeError("journal event hash invalid")
        terminal = event.event_sha256
        expected_previous = terminal
        expected_sequence += 1
    return terminal


class ResumableJournalFollower:
    """Poll one bounded remote journal while persisting verified continuation state."""

    def __init__(self, client: Any, checkpoints: JournalCheckpointStore) -> None:
        self.client = client
        self.checkpoints = checkpoints

    def poll_once(
        self,
        *,
        worker_id: str,
        stream_id: str,
        lease_id: str,
        fencing_token: int,
        limit: int = 100,
    ) -> dict[str, Any]:
        if fencing_token <= 0:
            raise ValueError("fencing_token must be positive")
        checkpoint = self.checkpoints.get(worker_id, stream_id)
        if checkpoint.complete:
            return {
                "worker_id": worker_id,
                "stream_id": stream_id,
                "cursor": checkpoint.cursor,
                "next_cursor": checkpoint.cursor,
                "head_sha256": checkpoint.last_event_sha256,
                "events": [],
                "complete": True,
                "reused_checkpoint": True,
            }
        result = self.client.call(
            "journal_poll",
            {
                "stream_id": stream_id,
                "cursor": checkpoint.cursor,
                "limit": int(limit),
                "lease_id": lease_id,
                "fencing_token": int(fencing_token),
            },
        )
        if not result.ok:
            raise RuntimeError(str(result.payload))
        page = dict(result.payload)
        if str(page.get("worker_id") or "") != worker_id:
            raise RuntimeError("journal page worker identity mismatch")
        if str(page.get("stream_id") or "") != stream_id:
            raise RuntimeError("journal page stream identity mismatch")
        if int(page.get("cursor", -1)) != checkpoint.cursor:
            raise RuntimeError("journal page cursor rollback/discontinuity")
        rows = page.get("events")
        if not isinstance(rows, list):
            raise RuntimeError("journal page events missing")
        terminal = _validate_incremental_events(
            [dict(v) for v in rows],
            cursor=checkpoint.cursor,
            previous_sha256=checkpoint.last_event_sha256,
        )
        next_cursor = int(page.get("next_cursor", -1))
        if next_cursor != checkpoint.cursor + len(rows):
            raise RuntimeError("journal page next_cursor mismatch")
        complete = bool(page.get("complete"))
        remote_head = str(page.get("head_sha256") or "")
        if complete and remote_head != terminal:
            raise RuntimeError("completed journal head mismatch")
        updated = JournalCheckpoint(
            worker_id=worker_id,
            stream_id=stream_id,
            cursor=next_cursor,
            last_event_sha256=terminal,
            complete=complete,
        )
        self.checkpoints.put(updated)
        return page

    def drain(
        self,
        *,
        worker_id: str,
        stream_id: str,
        lease_id: str,
        fencing_token: int,
        limit: int = 100,
        max_polls: int = 1000,
    ) -> JournalCheckpoint:
        for _ in range(max_polls):
            page = self.poll_once(
                worker_id=worker_id, stream_id=stream_id, lease_id=lease_id,
                fencing_token=fencing_token, limit=limit,
            )
            checkpoint = self.checkpoints.get(worker_id, stream_id)
            if checkpoint.complete:
                return checkpoint
            if not page.get("events"):
                return checkpoint
        raise RuntimeError("journal drain exceeded max_polls")
