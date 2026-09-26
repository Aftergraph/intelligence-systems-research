from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from jev_engineering.execution_journal import ExecutionJournal
from jev_engineering.relay_resilience import (
    JournalCheckpointStore,
    RelayGenerationStore,
    ResumableJournalFollower,
)


class FakeClient:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def call(self, operation, payload):
        self.calls.append((operation, dict(payload)))
        page = self.pages.pop(0)
        return type("Result", (), {"ok": True, "payload": page})()


def _page(stream_id: str, rows, cursor: int, *, complete: bool):
    journal = ExecutionJournal.from_list(rows)
    events = journal.to_list()[cursor:]
    return {
        "worker_id": "worker:a",
        "stream_id": stream_id,
        "cursor": cursor,
        "next_cursor": cursor + len(events),
        "head_sha256": journal.head_sha256,
        "events": events,
        "complete": complete,
    }


def test_relay_generation_store_survives_restart(tmp_path: Path):
    db = tmp_path / "relay.db"
    first = RelayGenerationStore(db)
    assert first.next_generation("worker:a") == 1
    assert first.next_generation("worker:a") == 2
    second = RelayGenerationStore(db)
    assert second.current_generation("worker:a") == 2
    assert second.next_generation("worker:a") == 3
    assert second.next_generation("worker:b") == 1


def test_resumable_journal_follower_persists_cursor_and_hash(tmp_path: Path):
    stream_id = "m:n:lease1"
    journal = ExecutionJournal()
    journal.append("one", {"x": 1}, observed_at="2026-09-25T00:00:00+00:00")
    first_rows = journal.to_list()
    journal.append("two", {"x": 2}, observed_at="2026-09-25T00:00:01+00:00")
    full_rows = journal.to_list()

    store = JournalCheckpointStore(tmp_path / "journal.db")
    first = FakeClient([_page(stream_id, first_rows, 0, complete=False)])
    follower = ResumableJournalFollower(first, store)
    page1 = follower.poll_once(
        worker_id="worker:a", stream_id=stream_id, lease_id="lease1", fencing_token=7
    )
    assert page1["next_cursor"] == 1
    checkpoint = store.get("worker:a", stream_id)
    assert checkpoint.cursor == 1
    assert checkpoint.last_event_sha256 == first_rows[-1]["event_sha256"]
    assert not checkpoint.complete

    # New process/object resumes from the durable cursor instead of replaying from zero.
    second = FakeClient([_page(stream_id, full_rows, 1, complete=True)])
    resumed = ResumableJournalFollower(second, JournalCheckpointStore(tmp_path / "journal.db"))
    page2 = resumed.poll_once(
        worker_id="worker:a", stream_id=stream_id, lease_id="lease1", fencing_token=7
    )
    assert second.calls[0][1]["cursor"] == 1
    assert page2["complete"] is True
    final = store.get("worker:a", stream_id)
    assert final.cursor == 2
    assert final.last_event_sha256 == full_rows[-1]["event_sha256"]
    assert final.complete


def test_resumable_journal_rejects_hash_chain_rollback(tmp_path: Path):
    stream_id = "m:n:lease1"
    journal = ExecutionJournal()
    journal.append("one", {}, observed_at="2026-09-25T00:00:00+00:00")
    rows = journal.to_list()
    store = JournalCheckpointStore(tmp_path / "journal.db")
    follower = ResumableJournalFollower(FakeClient([_page(stream_id, rows, 0, complete=False)]), store)
    follower.poll_once(worker_id="worker:a", stream_id=stream_id, lease_id="lease1", fencing_token=1)

    bad = dict(rows[0])
    bad["sequence"] = 1
    bad["previous_sha256"] = "0" * 64
    bad_page = {
        "worker_id": "worker:a",
        "stream_id": stream_id,
        "cursor": 1,
        "next_cursor": 2,
        "head_sha256": bad["event_sha256"],
        "events": [bad],
        "complete": True,
    }
    resumed = ResumableJournalFollower(FakeClient([bad_page]), store)
    with pytest.raises(RuntimeError, match="previous hash"):
        resumed.poll_once(worker_id="worker:a", stream_id=stream_id, lease_id="lease1", fencing_token=1)


def test_relay_hub_uses_durable_generation_store(tmp_path: Path):
    # Integration seam: RelayHubServer consults the durable store instead of resetting to generation 1.
    from jev_engineering.relay_fabric import RelayHubServer, RelayNodeAgent
    from jev_engineering.node_gateway import NodeGateway, OperationRegistry
    from jev_engineering.node_transport import NodeProtocol
    from jev_engineering.pki import EphemeralCertificateAuthority
    from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
    import time

    ca = EphemeralCertificateAuthority()
    relay_tls = ca.issue(common_name="relay.local", dns_names=["localhost"], ip_addresses=["127.0.0.1"], server=True)
    node_tls = ca.issue(common_name="worker:a", client=True)
    rcert, rkey, ca_file = relay_tls.write(tmp_path / "relay", prefix="relay")
    ncert, nkey, _ = node_tls.write(tmp_path / "node", prefix="node")
    node_signer = Ed25519ReceiptSigner.generate(key_id="worker:a")
    proto = NodeProtocol(signer=node_signer, verifier=Ed25519ReceiptVerifier({"worker:a": node_signer.public_key_bytes()}))
    gateway = NodeGateway(node_id="worker:a", protocol=proto, operations=OperationRegistry(), bind_peer_common_name=False)
    db = tmp_path / "generations.db"

    def wait(predicate):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if predicate(): return
            time.sleep(0.02)
        raise AssertionError("timeout")

    hub1 = RelayHubServer(host="127.0.0.1", port=0, ca_file=ca_file, certificate_file=rcert, private_key_file=rkey,
                          allowed_node_ids={"worker:a"}, allowed_coordinator_ids={"coordinator"}, generation_store=RelayGenerationStore(db)).start()
    h1,p1 = hub1.address
    node1 = RelayNodeAgent(node_id="worker:a", relay_host=h1, relay_port=p1, ca_file=ca_file, certificate_file=ncert, private_key_file=nkey,
                           gateway=gateway, reconnect=False).start()
    wait(lambda: hub1.session_generation("worker:a") == 1)
    node1.close(); hub1.close()

    hub2 = RelayHubServer(host="127.0.0.1", port=0, ca_file=ca_file, certificate_file=rcert, private_key_file=rkey,
                          allowed_node_ids={"worker:a"}, allowed_coordinator_ids={"coordinator"}, generation_store=RelayGenerationStore(db)).start()
    h2,p2 = hub2.address
    node2 = RelayNodeAgent(node_id="worker:a", relay_host=h2, relay_port=p2, ca_file=ca_file, certificate_file=ncert, private_key_file=nkey,
                           gateway=gateway, reconnect=False).start()
    wait(lambda: hub2.session_generation("worker:a") == 2)
    node2.close(); hub2.close()
