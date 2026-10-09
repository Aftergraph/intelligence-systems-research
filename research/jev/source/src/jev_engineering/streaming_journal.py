from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Iterable, Mapping

from .execution_journal import ExecutionEvent, ExecutionJournal
from .node_gateway import NodeCallContext, OperationRegistry


@dataclass(frozen=True, slots=True)
class JournalPage:
    worker_id: str
    stream_id: str
    cursor: int
    next_cursor: int
    head_sha256: str
    events: tuple[dict[str, Any], ...]
    complete: bool


class JournalStreamRegistry:
    """Server-owned hash-chained event streams exposed through bounded polling.

    This is intentionally pull-based rather than an arbitrary bidirectional socket:
    callers may only poll a named stream and cannot append or alter worker events.
    """

    def __init__(self) -> None:
        self._streams: dict[str, ExecutionJournal] = {}
        self._complete: set[str] = set()
        self._lock = Lock()

    def append(self, stream_id: str, event_type: str, data: Mapping[str, Any]) -> ExecutionEvent:
        if not stream_id.strip():
            raise ValueError("stream_id must be non-empty")
        with self._lock:
            if stream_id in self._complete:
                raise RuntimeError("cannot append to completed stream")
            journal = self._streams.setdefault(stream_id, ExecutionJournal())
            return journal.append(event_type, dict(data))

    def append_existing(self, stream_id: str, event: ExecutionEvent) -> None:
        """Append the exact already-minted journal event to the stream.

        This keeps the polled stream byte-for-byte/hash-for-hash aligned with the
        receipt-carried execution journal instead of minting a second timestamped event.
        """
        if not stream_id.strip():
            raise ValueError("stream_id must be non-empty")
        with self._lock:
            if stream_id in self._complete:
                raise RuntimeError("cannot append to completed stream")
            journal = self._streams.setdefault(stream_id, ExecutionJournal())
            journal.append_existing(event)

    def complete(self, stream_id: str) -> None:
        with self._lock:
            if stream_id not in self._streams:
                self._streams[stream_id] = ExecutionJournal()
            self._complete.add(stream_id)

    def page(self, stream_id: str, *, cursor: int = 0, limit: int = 100) -> JournalPage:
        if cursor < 0 or limit < 1 or limit > 1000:
            raise ValueError("invalid journal cursor/limit")
        with self._lock:
            journal = self._streams.get(stream_id)
            if journal is None:
                raise KeyError(stream_id)
            rows = journal.to_list()
            chunk = rows[cursor:cursor + limit]
            next_cursor = cursor + len(chunk)
            return JournalPage(
                worker_id="",
                stream_id=stream_id,
                cursor=cursor,
                next_cursor=next_cursor,
                head_sha256=journal.head_sha256,
                events=tuple(dict(v) for v in chunk),
                complete=stream_id in self._complete and next_cursor >= len(rows),
            )


class JournalStreamService:
    def __init__(self, registry: JournalStreamRegistry, leases=None) -> None:
        self.registry = registry
        self.leases = leases

    def poll(self, context: NodeCallContext) -> Mapping[str, Any]:
        payload = context.request.payload
        stream_id = str(payload.get("stream_id") or "")
        cursor = int(payload.get("cursor") or 0)
        limit = int(payload.get("limit") or 100)
        if self.leases is not None:
            from datetime import datetime, timezone
            lease_id = str(payload.get("lease_id") or "")
            fencing_token = int(payload.get("fencing_token") or 0)
            if not lease_id or fencing_token <= 0:
                raise RuntimeError("journal polling requires fenced lease binding")
            lease = self.leases.validate(lease_id, fencing_token=fencing_token, now=datetime.now(timezone.utc))
            if lease.worker_id != context.request.sender:
                raise RuntimeError("journal poll sender does not own fenced lease")
            if "journal_poll" not in lease.capabilities:
                raise RuntimeError("fenced lease does not grant journal_poll capability")
            if not stream_id.endswith(lease_id):
                raise RuntimeError("journal stream does not match fenced lease")
        page = self.registry.page(stream_id, cursor=cursor, limit=limit)
        body = asdict(page)
        body["worker_id"] = context.request.recipient
        return body

    def register(self, operations: OperationRegistry) -> None:
        operations.register("journal_poll", self.poll)


def verify_journal_pages(pages: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """Validate cursor continuity and hash-chain integrity for remote journal pages."""
    rows: list[dict[str, Any]] = []
    expected_cursor = 0
    terminal_head = ""
    complete = False
    for page in pages:
        cursor = int(page.get("cursor", -1))
        if cursor != expected_cursor:
            raise RuntimeError("journal page cursor discontinuity")
        events = page.get("events")
        if not isinstance(events, (list, tuple)):
            raise RuntimeError("journal page events missing")
        rows.extend(dict(v) for v in events)
        expected_cursor = int(page.get("next_cursor", -1))
        if expected_cursor != len(rows):
            raise RuntimeError("journal next_cursor mismatch")
        terminal_head = str(page.get("head_sha256") or "")
        complete = bool(page.get("complete"))
    if not complete:
        raise RuntimeError("journal stream is not complete")
    journal = ExecutionJournal.from_list(rows)
    if journal.head_sha256 != terminal_head:
        raise RuntimeError("journal stream head mismatch")
    return rows, terminal_head
