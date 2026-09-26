from dataclasses import replace
import pytest

from jev_engineering.execution_journal import ExecutionJournal


def test_execution_journal_hash_chain_roundtrip_and_tamper_detection():
    journal = ExecutionJournal()
    first = journal.append("started", {"node": "n1"}, observed_at="2026-09-25T00:00:00+00:00")
    second = journal.append("verified", {"verdict": "PASS"}, observed_at="2026-09-25T00:00:01+00:00")
    assert second.previous_sha256 == first.event_sha256
    loaded = ExecutionJournal.from_list(journal.to_list())
    assert loaded.head_sha256 == journal.head_sha256
    rows = journal.to_list()
    rows[1]["payload"] = {"verdict": "FAIL"}
    with pytest.raises(RuntimeError, match="hash invalid"):
        ExecutionJournal.from_list(rows)
