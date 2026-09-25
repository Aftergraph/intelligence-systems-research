from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Iterable, Mapping


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    sequence: int
    kind: str
    payload: dict[str, Any]
    observed_at: str
    previous_sha256: str
    event_sha256: str

    @classmethod
    def mint(
        cls,
        *,
        sequence: int,
        kind: str,
        payload: Mapping[str, Any],
        previous_sha256: str = "",
        observed_at: str | None = None,
    ) -> "ExecutionEvent":
        if sequence < 0:
            raise ValueError("sequence must be >= 0")
        if not kind.strip():
            raise ValueError("kind must be non-empty")
        body = {
            "sequence": sequence,
            "kind": kind,
            "payload": dict(payload),
            "observed_at": observed_at or datetime.now(timezone.utc).isoformat(),
            "previous_sha256": previous_sha256,
        }
        digest = hashlib.sha256(_canonical(body)).hexdigest()
        return cls(event_sha256=digest, **body)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExecutionJournal:
    """Append-only, hash-chained execution observations.

    Events are evidence inputs, not proof by themselves. A verifier still decides
    whether the observed trajectory satisfies mission acceptance.
    """

    def __init__(self, events: Iterable[ExecutionEvent] = ()) -> None:
        self._events: list[ExecutionEvent] = []
        for event in events:
            self.append_existing(event)

    def append(self, kind: str, payload: Mapping[str, Any], *, observed_at: str | None = None) -> ExecutionEvent:
        previous = self._events[-1].event_sha256 if self._events else ""
        event = ExecutionEvent.mint(
            sequence=len(self._events), kind=kind, payload=payload,
            previous_sha256=previous, observed_at=observed_at,
        )
        self._events.append(event)
        return event

    def append_existing(self, event: ExecutionEvent) -> None:
        expected_seq = len(self._events)
        expected_prev = self._events[-1].event_sha256 if self._events else ""
        if event.sequence != expected_seq:
            raise RuntimeError("execution journal sequence gap")
        if event.previous_sha256 != expected_prev:
            raise RuntimeError("execution journal previous hash mismatch")
        body = {
            "sequence": event.sequence,
            "kind": event.kind,
            "payload": event.payload,
            "observed_at": event.observed_at,
            "previous_sha256": event.previous_sha256,
        }
        if hashlib.sha256(_canonical(body)).hexdigest() != event.event_sha256:
            raise RuntimeError("execution journal event hash invalid")
        self._events.append(event)

    @property
    def head_sha256(self) -> str:
        return self._events[-1].event_sha256 if self._events else ""

    def events(self) -> tuple[ExecutionEvent, ...]:
        return tuple(self._events)

    def to_list(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self._events]

    @classmethod
    def from_list(cls, rows: Iterable[Mapping[str, Any]]) -> "ExecutionJournal":
        return cls(ExecutionEvent(
            sequence=int(row["sequence"]),
            kind=str(row["kind"]),
            payload=dict(row.get("payload") or {}),
            observed_at=str(row["observed_at"]),
            previous_sha256=str(row.get("previous_sha256") or ""),
            event_sha256=str(row["event_sha256"]),
        ) for row in rows)
