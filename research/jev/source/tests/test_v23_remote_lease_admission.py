from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jev_engineering.durable_state import SqliteLeaseStore
from jev_engineering.node_gateway import NodeCallContext, OperationRegistry
from jev_engineering.node_transport import NodeRequest
from jev_engineering.remote_control import LeaseControlService


def _ctx(sender: str, payload: dict):
    return NodeCallContext(NodeRequest(
        request_id="req", sender=sender, recipient="worker:lenovo", operation="lease_issue",
        payload=payload, sent_at=datetime.now(timezone.utc).isoformat(), nonce="n",
    ))


def test_authorized_coordinator_can_issue_remote_fenced_lease(tmp_path: Path):
    store = SqliteLeaseStore(tmp_path / "leases.db")
    service = LeaseControlService(
        store,
        authorized_issuers=frozenset({"coordinator"}),
        allowed_capabilities=frozenset({"verify_candidate", "journal_poll"}),
    )
    result = service.issue(_ctx("coordinator", {
        "node_id": "node:verify",
        "authority_grant_id": "grant:verify",
        "capabilities": ["verify_candidate", "journal_poll"],
        "ttl_seconds": 300,
    }))
    lease = store.get(result["lease_id"])
    assert lease.worker_id == "coordinator"
    assert lease.node_id == "node:verify"
    assert lease.fencing_token == 1
    assert lease.capabilities == frozenset({"verify_candidate", "journal_poll"})


def test_remote_lease_issue_rejects_unauthorized_issuer_and_capability_escalation(tmp_path: Path):
    store = SqliteLeaseStore(tmp_path / "leases.db")
    service = LeaseControlService(
        store,
        authorized_issuers=frozenset({"coordinator"}),
        allowed_capabilities=frozenset({"verify_candidate"}),
    )
    try:
        service.issue(_ctx("attacker", {
            "node_id": "node:verify", "authority_grant_id": "grant", "capabilities": ["verify_candidate"], "ttl_seconds": 60,
        }))
    except RuntimeError as exc:
        assert "authorized" in str(exc).lower()
    else:
        raise AssertionError("unauthorized lease issuer was accepted")

    try:
        service.issue(_ctx("coordinator", {
            "node_id": "node:verify", "authority_grant_id": "grant", "capabilities": ["shell"], "ttl_seconds": 60,
        }))
    except RuntimeError as exc:
        assert "capabil" in str(exc).lower()
    else:
        raise AssertionError("capability escalation was accepted")


def test_lease_issue_is_registered_only_when_issuer_policy_exists(tmp_path: Path):
    store = SqliteLeaseStore(tmp_path / "leases.db")
    ops = OperationRegistry()
    LeaseControlService(store).register(ops)
    try:
        ops.execute(_ctx("coordinator", {
            "node_id": "node:verify", "authority_grant_id": "grant", "capabilities": ["verify_candidate"], "ttl_seconds": 60,
        }))
    except RuntimeError as exc:
        assert "unsupported" in str(exc).lower()
    else:
        raise AssertionError("lease_issue unexpectedly available without issuer policy")
