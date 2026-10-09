import pytest

from jev_engineering.streaming_journal import JournalStreamRegistry, verify_journal_pages


def test_stream_pages_are_hash_chain_verified():
    reg = JournalStreamRegistry()
    reg.append("s", "work.started", {"step": 1})
    reg.append("s", "work.progress", {"step": 2})
    reg.complete("s")
    p1 = reg.page("s", cursor=0, limit=1)
    p2 = reg.page("s", cursor=p1.next_cursor, limit=1)
    rows, head = verify_journal_pages([
        {**p1.__dict__} if hasattr(p1, "__dict__") else {
            "cursor": p1.cursor, "next_cursor": p1.next_cursor, "head_sha256": p1.head_sha256,
            "events": list(p1.events), "complete": p1.complete,
        },
        {"cursor": p2.cursor, "next_cursor": p2.next_cursor, "head_sha256": p2.head_sha256,
         "events": list(p2.events), "complete": p2.complete},
    ])
    assert len(rows) == 2
    assert head == p2.head_sha256


def test_incomplete_stream_is_rejected():
    reg = JournalStreamRegistry()
    reg.append("s", "work.started", {})
    p = reg.page("s")
    with pytest.raises(RuntimeError, match="not complete"):
        verify_journal_pages([{
            "cursor": p.cursor, "next_cursor": p.next_cursor, "head_sha256": p.head_sha256,
            "events": list(p.events), "complete": p.complete,
        }])
