from __future__ import annotations

import base64
import json
from pathlib import Path

from jev_engineering.node_daemon import NodeAgent, NodeAgentConfig, generate_node_config_template
from jev_engineering.pki import EphemeralCertificateAuthority
from jev_engineering.public_receipts import Ed25519ReceiptSigner


def _config(tmp_path: Path) -> Path:
    ca = EphemeralCertificateAuthority()
    node_tls = ca.issue(common_name="localhost", dns_names=["localhost"], ip_addresses=["127.0.0.1"], server=True)
    cert, key, ca_file = node_tls.write(tmp_path / "tls", prefix="node")
    node_signer = Ed25519ReceiptSigner.generate(key_id="node:worker")
    signing_key = node_signer.write_private_key(tmp_path / "secrets" / "node.ed25519.key")
    peer = Ed25519ReceiptSigner.generate(key_id="coordinator")
    workspace = tmp_path / "workspace"; workspace.mkdir()
    (workspace / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    payload = {
        "node_id": "worker",
        "host": "127.0.0.1",
        "port": 0,
        "ca_file": str(ca_file),
        "certificate_file": str(cert),
        "private_key_file": str(key),
        "signing_key_file": str(signing_key),
        "signing_key_id": "node:worker",
        "peer_public_keys": {"coordinator": base64.b64encode(peer.public_key_bytes()).decode()},
        "lease_db": str(tmp_path / "state" / "leases.db"),
        "verifier_workspace": str(workspace),
        "verifier_command": ["python", "-m", "pytest", "-q"],
        "verifier_name": "worker-pytest"
    }
    path = tmp_path / "node.json"; path.write_text(json.dumps(payload))
    return path


def test_signing_key_roundtrip(tmp_path: Path):
    signer = Ed25519ReceiptSigner.generate(key_id="k")
    path = signer.write_private_key(tmp_path / "key")
    loaded = Ed25519ReceiptSigner.load_private_key(key_id="k", path=path)
    assert loaded.public_key_bytes() == signer.public_key_bytes()


def test_node_agent_config_and_start(tmp_path: Path):
    cfg = NodeAgentConfig.load_json(_config(tmp_path))
    assert cfg.public_summary()["tls_required"] is True
    with NodeAgent(cfg) as node:
        host, port = node.address
        assert host == "127.0.0.1" and port > 0


def test_template_contains_no_secret_values():
    template = generate_node_config_template(node_id="jonas-lenovo")
    blob = json.dumps(template)
    assert "PRIVATE_KEY" not in blob
    assert template["node_id"] == "jonas-lenovo"
