from pathlib import Path
import sys

from jev_engineering.node_gateway import NodeCallContext, OperationRegistry
from jev_engineering.node_transport import NodeRequest
from jev_engineering.proof_graph import workspace_tree_hash
from jev_engineering.remote_control import PreconfiguredVerifierCapability


def request(payload):
    return NodeCallContext(NodeRequest(
        request_id="r", sender="worker", recipient="node", operation="verify_candidate",
        payload=payload, sent_at="2026-09-25T00:00:00+00:00", nonce="n",
    ))


def test_preconfigured_verifier_executes_server_owned_command_and_binds_candidate(tmp_path: Path):
    (tmp_path / "calc.py").write_text("def add(a,b): return a+b\n")
    sha = "sha256:" + workspace_tree_hash(tmp_path)
    cap = PreconfiguredVerifierCapability(
        workspace=tmp_path,
        command=(sys.executable, "-c", "from calc import add; assert add(2,3)==5"),
        verifier_name="sentinel",
    )
    payload = {
        "mission_id":"m", "node_id":"n", "execution_context_id":"ctx", "lease_id":"l",
        "fencing_token":1, "authority_grant_id":"g", "candidate_sha":sha, "operation":"verify_candidate",
    }
    out = cap.handle(request(payload))
    assert out["verdict"] == "PASS"
    assert out["evidence"]["exit_code"] == 0
    assert len(out["evidence"]["execution_events"]) == 2


def test_preconfigured_verifier_rejects_stale_candidate_hash(tmp_path: Path):
    (tmp_path / "calc.py").write_text("x=1\n")
    cap = PreconfiguredVerifierCapability(workspace=tmp_path, command=(sys.executable,"-c","pass"), verifier_name="sentinel")
    payload = {
        "mission_id":"m", "node_id":"n", "execution_context_id":"ctx", "lease_id":"l",
        "fencing_token":1, "authority_grant_id":"g", "candidate_sha":"sha256:stale", "operation":"verify_candidate",
    }
    import pytest
    with pytest.raises(RuntimeError, match="candidate SHA"):
        cap.handle(request(payload))
