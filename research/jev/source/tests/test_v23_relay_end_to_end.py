from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import time

from jev_engineering.node_daemon import NodeAgentConfig, build_node_gateway
from jev_engineering.node_transport import NodeProtocol
from jev_engineering.pki import EphemeralCertificateAuthority
from jev_engineering.proof_graph import workspace_tree_hash
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
from jev_engineering.relay_fabric import RelayCoordinatorClient, RelayHubServer, RelayNodeAgent
from jev_engineering.remote_execution import RemoteExecutionCoordinator, RemoteWorkOrder
from jev_engineering.remote_worker import RemoteWorkerClient
from jev_engineering.streaming_journal import verify_journal_pages


def _wait(predicate, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate(): return
        time.sleep(0.02)
    raise AssertionError("condition not reached")


def test_relay_path_can_issue_fenced_lease_verify_and_read_journal(tmp_path: Path):
    ca = EphemeralCertificateAuthority()
    relay_tls = ca.issue(common_name="relay.local", dns_names=["localhost"], ip_addresses=["127.0.0.1"], server=True)
    node_tls = ca.issue(common_name="worker:relay", client=True)
    coord_tls = ca.issue(common_name="coordinator", client=True)
    rcert, rkey, ca_file = relay_tls.write(tmp_path / "relay", prefix="relay")
    ncert, nkey, _ = node_tls.write(tmp_path / "node-tls", prefix="node")
    ccert, ckey, _ = coord_tls.write(tmp_path / "coord-tls", prefix="coord")

    node_signer = Ed25519ReceiptSigner.generate(key_id="worker:relay")
    coord_signer = Ed25519ReceiptSigner.generate(key_id="coordinator")
    node_signer.write_private_key(tmp_path / "node.ed25519")
    coord_signer.write_private_key(tmp_path / "coord.ed25519")

    workspace = tmp_path / "workspace"; workspace.mkdir()
    (workspace / "candidate.py").write_text("VALUE = 42\n", encoding="utf-8")
    node_cfg_path = tmp_path / "node.json"
    node_cfg_path.write_text(json.dumps({
        "node_id":"worker:relay", "host":"127.0.0.1", "port":0,
        "ca_file":str(ca_file), "certificate_file":str(ncert), "private_key_file":str(nkey),
        "signing_key_file":str(tmp_path / "node.ed25519"), "signing_key_id":"worker:relay",
        "peer_public_keys":{"coordinator":base64.b64encode(coord_signer.public_key_bytes()).decode("ascii")},
        "peer_sender_key_ids":{"coordinator":"coordinator"},
        "lease_issuer_ids":["coordinator"],
        "lease_allowed_capabilities":["verify_candidate","journal_poll","lease_heartbeat","lease_renew"],
        "lease_db":str(tmp_path / "leases.db"), "verifier_workspace":str(workspace),
        "verifier_command":[sys.executable,"-c","import candidate; assert candidate.VALUE == 42"],
        "verifier_name":"relay-py",
    }), encoding="utf-8")
    gateway = build_node_gateway(NodeAgentConfig.load_json(node_cfg_path))

    coord_protocol = NodeProtocol(
        signer=coord_signer,
        verifier=Ed25519ReceiptVerifier({
            "coordinator": coord_signer.public_key_bytes(),
            "worker:relay": node_signer.public_key_bytes(),
        }),
    )

    with RelayHubServer(
        host="127.0.0.1", port=0, ca_file=ca_file,
        certificate_file=rcert, private_key_file=rkey,
        allowed_node_ids={"worker:relay"}, allowed_coordinator_ids={"coordinator"},
    ) as hub:
        host, port = hub.address
        with RelayNodeAgent(
            node_id="worker:relay", relay_host=host, relay_port=port,
            ca_file=ca_file, certificate_file=ncert, private_key_file=nkey,
            gateway=gateway,
        ) as node:
            _wait(lambda: node.registered)
            transport = RelayCoordinatorClient(
                coordinator_id="coordinator", relay_host=host, relay_port=port,
                ca_file=ca_file, certificate_file=ccert, private_key_file=ckey,
            )
            remote = RemoteWorkerClient(
                sender_id="coordinator", worker_id="worker:relay", protocol=coord_protocol,
                send=transport.send,
            )
            issued = remote.call("lease_issue", {
                "node_id":"node:verify", "authority_grant_id":"grant:verify",
                "capabilities":["verify_candidate","journal_poll","lease_heartbeat","lease_renew"],
                "ttl_seconds":300,
            })
            assert issued.ok
            lease = issued.payload
            candidate_sha = "sha256:" + workspace_tree_hash(workspace)
            order = RemoteWorkOrder(
                mission_id="mission:v23", node_id="node:verify", execution_context_id="ctx:v23",
                lease_id=lease["lease_id"], fencing_token=lease["fencing_token"],
                authority_grant_id="grant:verify", candidate_sha=candidate_sha,
            )
            receipt = RemoteExecutionCoordinator(remote).execute(order)
            assert receipt.passed
            stream_id = receipt.evidence["stream_id"]
            page = remote.call("journal_poll", {
                "stream_id":stream_id, "cursor":0, "limit":100,
                "lease_id":lease["lease_id"], "fencing_token":lease["fencing_token"],
            })
            assert page.ok
            rows, head = verify_journal_pages([page.payload])
            assert len(rows) == 2
            assert head == receipt.evidence["execution_journal_head_sha256"]
            assert node.local_listen_port is None
