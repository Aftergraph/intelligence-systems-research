from __future__ import annotations

import base64
import json
from pathlib import Path

from jev_engineering.node_client import NodeClientConfig, NodeClientSession
from jev_engineering.node_daemon import NodeAgent, NodeAgentConfig
from jev_engineering.pki import EphemeralCertificateAuthority
from jev_engineering.public_receipts import Ed25519ReceiptSigner


def test_deployable_client_can_probe_deployable_node(tmp_path: Path):
    ca = EphemeralCertificateAuthority()
    server_tls = ca.issue(common_name="localhost", dns_names=["localhost"], ip_addresses=["127.0.0.1"], server=True)
    client_tls = ca.issue(common_name="coordinator", client=True)
    scert, skey, ca_file = server_tls.write(tmp_path / "server", prefix="node")
    ccert, ckey, _ = client_tls.write(tmp_path / "client", prefix="coord")
    node_signer = Ed25519ReceiptSigner.generate(key_id="worker")
    coord_signer = Ed25519ReceiptSigner.generate(key_id="coordinator")
    node_key = node_signer.write_private_key(tmp_path / "node.ed25519")
    coord_key = coord_signer.write_private_key(tmp_path / "coord.ed25519")
    workspace = tmp_path / "workspace"; workspace.mkdir()
    (workspace / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    node_cfg_path = tmp_path / "node.json"
    node_cfg_path.write_text(json.dumps({
        "node_id":"worker", "host":"127.0.0.1", "port":0,
        "ca_file":str(ca_file), "certificate_file":str(scert), "private_key_file":str(skey),
        "signing_key_file":str(node_key), "signing_key_id":"worker",
        "peer_public_keys":{"coordinator":base64.b64encode(coord_signer.public_key_bytes()).decode()},
        "lease_db":str(tmp_path / "leases.db"), "verifier_workspace":str(workspace),
        "verifier_command":["python","-m","pytest","-q"], "verifier_name":"worker-pytest"
    }))
    with NodeAgent(NodeAgentConfig.load_json(node_cfg_path)) as node:
        _, port = node.address
        client_cfg_path = tmp_path / "client.json"
        client_cfg_path.write_text(json.dumps({
            "sender_id":"coordinator", "worker_id":"worker",
            "endpoint_url":f"https://localhost:{port}/v1/node/call",
            "ca_file":str(ca_file), "certificate_file":str(ccert), "private_key_file":str(ckey),
            "signing_key_file":str(coord_key), "signing_key_id":"coordinator",
            "worker_public_key_b64":base64.b64encode(node_signer.public_key_bytes()).decode(),
        }))
        with NodeClientSession(NodeClientConfig.load_json(client_cfg_path)) as session:
            description = session.describe()
            assert description["node_id"] == "worker"
            assert description["arbitrary_shell"] is False
            assert "verify_candidate" in description["capabilities"]
