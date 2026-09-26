from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from jev_engineering.physical_pair import PhysicalPairManifest, generate_physical_pair_template
from jev_engineering.public_receipts import Ed25519ReceiptSigner
from jev_engineering.pki import EphemeralCertificateAuthority


def _write_pair(tmp_path: Path, *, same_domain: bool = False) -> Path:
    ca = EphemeralCertificateAuthority()
    relay = ca.issue(common_name="relay.local", dns_names=["localhost"], ip_addresses=["127.0.0.1"], server=True)
    coord = ca.issue(common_name="coordinator", client=True)
    rcert, rkey, ca_file = relay.write(tmp_path / "relay-tls", prefix="relay")
    ccert, ckey, _ = coord.write(tmp_path / "coord-tls", prefix="coord")
    coord_signer = Ed25519ReceiptSigner.generate(key_id="coordinator")
    coord_signer.write_private_key(tmp_path / "coord.key")

    hub = tmp_path / "relay-hub.json"
    hub.write_text(json.dumps({
        "host":"127.0.0.1","port":9444,"ca_file":str(ca_file),
        "certificate_file":str(rcert),"private_key_file":str(rkey),
        "allowed_node_ids":["worker:jonas-lenovo","worker:vds"],
        "allowed_coordinator_ids":["coordinator"],
    }), encoding="utf-8")

    nodes = []
    for idx, node_id in enumerate(("worker:jonas-lenovo", "worker:vds")):
        d = tmp_path / ("lenovo" if idx == 0 else "vds"); d.mkdir()
        node_tls = ca.issue(common_name=node_id, client=True)
        ncert, nkey, _ = node_tls.write(d / "tls", prefix="node")
        node_signer = Ed25519ReceiptSigner.generate(key_id=node_id)
        node_signer.write_private_key(d / "node.key")
        workspace = d / "workspace"; workspace.mkdir()
        node_json = d / "node.json"
        node_json.write_text(json.dumps({
            "node_id":node_id,"host":"127.0.0.1","port":0,
            "ca_file":str(ca_file),"certificate_file":str(ncert),"private_key_file":str(nkey),
            "signing_key_file":str(d / "node.key"),"signing_key_id":node_id,
            "peer_public_keys":{"coordinator":base64.b64encode(coord_signer.public_key_bytes()).decode()},
            "peer_sender_key_ids":{"coordinator":"coordinator"},
            "lease_issuer_ids":["coordinator"],
            "lease_allowed_capabilities":["verify_candidate","journal_poll","lease_heartbeat","lease_renew"],
            "lease_db":str(d / "leases.db"),"verifier_workspace":str(workspace),
            "verifier_command":["python","-c","print('ok')"],"verifier_name":node_id,
        }), encoding="utf-8")
        relay_node = d / "relay-node.json"
        relay_node.write_text(json.dumps({
            "node_config_file":str(node_json),"relay_host":"relay.example","relay_port":9444,
            "ca_file":str(ca_file),"certificate_file":str(ncert),"private_key_file":str(nkey),
        }), encoding="utf-8")
        relay_client = d / "relay-client.json"
        relay_client.write_text(json.dumps({
            "sender_id":"coordinator","worker_id":node_id,"relay_host":"relay.example","relay_port":9444,
            "ca_file":str(ca_file),"certificate_file":str(ccert),"private_key_file":str(ckey),
            "signing_key_file":str(tmp_path / "coord.key"),"signing_key_id":"coordinator",
            "worker_public_key_b64":base64.b64encode(node_signer.public_key_bytes()).decode(),
        }), encoding="utf-8")
        nodes.append({
            "node_id":node_id,
            "trust_domain":"same" if same_domain else f"td:{idx}",
            "relay_node_config":str(relay_node),
            "relay_client_config":str(relay_client),
        })
    manifest = tmp_path / "pair.json"
    manifest.write_text(json.dumps({"relay_hub_config":str(hub),"nodes":nodes}), encoding="utf-8")
    return manifest


def test_physical_pair_doctor_checks_distinct_identity_and_trust_domains(tmp_path: Path):
    report = PhysicalPairManifest.load_json(_write_pair(tmp_path)).doctor()
    assert report["status"] == "READY"
    assert len(report["nodes"]) == 2
    assert report["distinct_trust_domains"] is True


def test_physical_pair_rejects_same_trust_domain(tmp_path: Path):
    with pytest.raises(ValueError, match="trust domains"):
        PhysicalPairManifest.load_json(_write_pair(tmp_path, same_domain=True))


def test_template_is_secret_free_and_names_lenovo_and_vds():
    payload = generate_physical_pair_template()
    raw = json.dumps(payload)
    assert "jonas-lenovo" in raw and "worker:vds" in raw
    assert "apikey_" not in raw and "dgr_live_" not in raw
