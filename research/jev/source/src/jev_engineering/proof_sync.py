from __future__ import annotations

from pathlib import Path
import json
import sqlite3

from .proof_graph import ProofGraph


class SqliteProofGraphStore:
    """Optimistic-concurrency store for synchronizing ProofGraph snapshots."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        con = self._connect()
        try:
            con.execute("CREATE TABLE IF NOT EXISTS proof_graphs (graph_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload_json TEXT NOT NULL)")
        finally:
            con.close()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
        return con

    def read(self, graph_id: str) -> tuple[ProofGraph, int]:
        con = self._connect()
        try:
            row = con.execute("SELECT revision,payload_json FROM proof_graphs WHERE graph_id=?", (graph_id,)).fetchone()
        finally:
            con.close()
        if row is None:
            return ProofGraph(), 0
        payload = json.loads(row["payload_json"])
        return ProofGraph.from_dict(payload), int(row["revision"])

    def compare_and_swap(self, graph_id: str, *, expected_revision: int, graph: ProofGraph) -> int:
        payload = json.dumps(graph.to_dict(), sort_keys=True, separators=(",", ":"))
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT revision FROM proof_graphs WHERE graph_id=?", (graph_id,)).fetchone()
            actual = int(row["revision"]) if row else 0
            if actual != expected_revision:
                con.execute("ROLLBACK")
                raise RuntimeError(f"proof graph revision conflict: expected {expected_revision}, observed {actual}")
            next_revision = actual + 1
            con.execute(
                "INSERT INTO proof_graphs(graph_id,revision,payload_json) VALUES(?,?,?) ON CONFLICT(graph_id) DO UPDATE SET revision=excluded.revision,payload_json=excluded.payload_json",
                (graph_id, next_revision, payload),
            )
            con.execute("COMMIT")
        finally:
            con.close()
        return next_revision
