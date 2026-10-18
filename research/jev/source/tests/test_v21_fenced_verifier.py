from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from jev_engineering.durable_state import SqliteLeaseStore
from jev_engineering.node_gateway import NodeCallContext
from jev_engineering.node_transport import NodeRequest
from jev_engineering.proof_graph import workspace_tree_hash
from jev_engineering.remote_control import FencedPreconfiguredVerifierCapability
from jev_engineering.remote_execution import RemoteWorkOrder


def _ctx(order, sender="coord"):
    return NodeCallContext(NodeRequest(
        request_id="r", sender=sender, recipient="worker", operation="verify_candidate",
        payload=order.to_payload(), sent_at=datetime.now(timezone.utc).isoformat(), nonce="n",
    ))


def test_fenced_verifier_rejects_stale_token(tmp_path: Path):
    ws = tmp_path / "ws"; ws.mkdir(); (ws / "x.py").write_text("X=1\n")
    leases = SqliteLeaseStore(tmp_path / "l.db")
    now = datetime.now(timezone.utc)
    lease = leases.issue(node_id="n", worker_id="coord", authority_grant_id="g", capabilities={"verify_candidate"}, ttl=timedelta(minutes=5), now=now)
    order = RemoteWorkOrder("m", "n", "ctx", lease.lease_id, lease.fencing_token + 1, "g", "sha256:" + workspace_tree_hash(ws))
    cap = FencedPreconfiguredVerifierCapability(workspace=ws, command=("python", "-c", "pass"), verifier_name="v", leases=leases)
    with pytest.raises(RuntimeError):
        cap.handle(_ctx(order))


def test_fenced_verifier_executes_fixed_command(tmp_path: Path):
    ws = tmp_path / "ws"; ws.mkdir(); (ws / "x.py").write_text("X=1\n")
    leases = SqliteLeaseStore(tmp_path / "l.db")
    now = datetime.now(timezone.utc)
    lease = leases.issue(node_id="n", worker_id="coord", authority_grant_id="g", capabilities={"verify_candidate"}, ttl=timedelta(minutes=5), now=now)
    order = RemoteWorkOrder("m", "n", "ctx", lease.lease_id, lease.fencing_token, "g", "sha256:" + workspace_tree_hash(ws))
    cap = FencedPreconfiguredVerifierCapability(workspace=ws, command=("python", "-c", "import x; assert x.X==1"), verifier_name="v", leases=leases)
    result = cap.handle(_ctx(order))
    assert result["verdict"] == "PASS"
    assert result["evidence"]["mode"] == "fenced-preconfigured-subprocess"
