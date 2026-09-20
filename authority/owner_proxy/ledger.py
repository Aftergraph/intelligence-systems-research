"""Append-only, hash-chained delegation ledger (spec §7, §8).

``data/delegation_ledger.jsonl`` -- one JSON object per line. Each row carries an
explicit ``actor`` / ``principal`` / ``delegation_ref`` / ``provenance`` and NEVER
relies on git-author attribution (the clone's git identity differs from the
owner's approval principal, so an agent commit is not the owner's hand -- spec §6
Principal note).

Chaining: ``entry_sha256 = sha256(canonical(row minus entry_sha256))`` and each
row's ``prev_sha256`` is the prior row's ``entry_sha256`` (null for seq 1). That
makes truncation, insertion, deletion and reordering detectable -- the CI audit
recomputes the whole chain (spec §3, §8 Ledger integrity).

The ledger append is the COMMIT POINT: no ledger row means the act did not happen
(spec §5). The path is new and sits outside the 30-path manifest, so appending
never moves the calibration pin ``dc5d7a94...`` (spec §7 independence).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import os

ROW_FIELDS: tuple[str, ...] = (
    "seq",
    "prev_sha256",
    "ts",
    "actor",
    "principal",
    "delegation_ref",
    "action",
    "tier",
    "target",
    "approval_record",
    "bindings",
)


def _canonical(row: dict[str, Any]) -> str:
    # Repo-wide canonicalization (matches ADR-008 / integrity.py).
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _row_sha(row: dict[str, Any]) -> str:
    body = {k: v for k, v in row.items() if k != "entry_sha256"}
    return sha256(_canonical(body).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LedgerResult:
    ok: bool
    reason: str | None
    seq: int | None = None
    entry_sha256: str | None = None


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        rows.append(json.loads(raw))
    return rows


def head_seq(path: Path | str) -> int:
    """Last committed seq (0 when the ledger is empty/nonexistent)."""
    rows = _read_rows(Path(path))
    return int(rows[-1]["seq"]) if rows else 0


def verify_chain(path: Path | str) -> tuple[bool, str | None]:
    """Recompute the whole chain. Returns (ok, reason)."""
    rows = _read_rows(Path(path))
    prev: str | None = None
    for i, row in enumerate(rows, start=1):
        missing = [f for f in ROW_FIELDS if f not in row]
        if missing:
            return False, f"ledger_row_{i}_missing:{','.join(missing)}"
        if int(row["seq"]) != i:
            return False, f"ledger_seq_gap_at_{i}"
        if row["prev_sha256"] != prev:
            return False, f"ledger_chain_break_at_{i}"
        if _row_sha(row) != row["entry_sha256"]:
            return False, f"ledger_entry_hash_bad_at_{i}"
        prev = row["entry_sha256"]
    return True, None


def append_entry(
    path: Path | str,
    *,
    ts: str,
    actor: str,
    principal: str,
    delegation_ref: str,
    action: str,
    tier: str,
    target: str,
    approval_record: str,
    bindings: dict[str, Any],
    expected_seq: int | None = None,
) -> LedgerResult:
    """Verify the existing chain, then append one committed row.

    Fail-closed on any chain defect (spec §8 Ledger integrity): a damaged chain
    refuses BOTH to sign and to append. ``expected_seq`` (when given) is the seq
    the caller already embedded in the approval record's provenance; a mismatch
    means a concurrent append slipped in and the act is aborted.
    """
    path = Path(path)
    ok, reason = verify_chain(path)
    if not ok:
        return LedgerResult(False, reason)
    rows = _read_rows(path)
    seq = len(rows) + 1
    if expected_seq is not None and seq != expected_seq:
        return LedgerResult(False, f"ledger_seq_race_expected_{expected_seq}_got_{seq}")
    prev = rows[-1]["entry_sha256"] if rows else None
    row: dict[str, Any] = {
        "seq": seq,
        "prev_sha256": prev,
        "ts": ts,
        "actor": actor,
        "principal": principal,
        "delegation_ref": delegation_ref,
        "action": action,
        "tier": tier,
        "target": target,
        "approval_record": approval_record,
        "bindings": bindings,
    }
    row["entry_sha256"] = _row_sha(row)
    line = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    # Re-verify after write; roll back the byte append if it corrupted the chain.
    ok2, reason2 = verify_chain(path)
    if not ok2:
        _truncate_to(path, len(rows))
        return LedgerResult(False, f"ledger_post_write_chain_bad:{reason2}")
    _ = existed
    return LedgerResult(True, None, seq=seq, entry_sha256=row["entry_sha256"])


def _truncate_to(path: Path, keep_rows: int) -> None:
    rows = _read_rows(path)[:keep_rows]
    data = "".join(
        json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for r in rows
    )
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()