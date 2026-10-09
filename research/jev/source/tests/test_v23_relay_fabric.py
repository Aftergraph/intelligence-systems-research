from __future__ import annotations

import base64
from pathlib import Path
import time

import pytest

from jev_engineering.node_gateway import NodeGateway, OperationRegistry
from jev_engineering.node_transport import NodeProtocol
from jev_engineering.pki import EphemeralCertificateAuthority
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
from jev_engineering.relay_fabric import (
    RelayCoordinatorClient,
    RelayHubServer,
    RelayNodeAgent,
)
from jev_engineering.remote_worker import RemoteWorkerClient


def _wait(predicate, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condition not reached before timeout")


def _stack(tmp_path: Path):
    ca = EphemeralCertificateAuthority()
    relay_tls = ca.issue(
        common_name="relay.local",
        dns_names=["localhost"],
        ip_addresses=["127.0.0.1"],
        server=True,
    )
    node_tls = ca.issue(common_name="worker:lenovo", client=True)
    coord_tls = ca.issue(common_name="coordinator", client=True)
    rcert, rkey, ca_file = relay_tls.write(tmp_path / "relay", prefix="relay")
    ncert, nkey, _ = node_tls.write(tmp_path / "node", prefix="node")
    ccert, ckey, _ = coord_tls.write(tmp_path / "coord", prefix="coord")

    node_signer = Ed25519ReceiptSigner.generate(key_id="worker:lenovo")
    coord_signer = Ed25519ReceiptSigner.generate(key_id="coordinator")
    node_protocol = NodeProtocol(
        signer=node_signer,
        verifier=Ed25519ReceiptVerifier({
            "worker:lenovo": node_signer.public_key_bytes(),
            "coordinator": coord_signer.public_key_bytes(),
        }),
    )
    coord_protocol = NodeProtocol(
        signer=coord_signer,
        verifier=Ed25519ReceiptVerifier({
            "coordinator": coord_signer.public_key_bytes(),
            "worker:lenovo": node_signer.public_key_bytes(),
        }),
    )
    ops = OperationRegistry()
    ops.register("node_describe", lambda ctx: {
        "node_id": "worker:lenovo",
        "transport": "outbound-relay",
        "arbitrary_shell": False,
    })
    gateway = NodeGateway(node_id="worker:lenovo", protocol=node_protocol, operations=ops)
    return {
        "ca": ca,
        "ca_file": ca_file,
        "relay_cert": rcert,
        "relay_key": rkey,
        "node_cert": ncert,
        "node_key": nkey,
        "coord_cert": ccert,
        "coord_key": ckey,
        "node_protocol": node_protocol,
        "coord_protocol": coord_protocol,
        "gateway": gateway,
    }


def test_outbound_only_node_can_receive_signed_calls_through_relay(tmp_path: Path):
    s = _stack(tmp_path)
    with RelayHubServer(
        host="127.0.0.1",
        port=0,
        ca_file=s["ca_file"],
        certificate_file=s["relay_cert"],
        private_key_file=s["relay_key"],
        allowed_node_ids={"worker:lenovo"},
        allowed_coordinator_ids={"coordinator"},
    ) as hub:
        host, port = hub.address
        with RelayNodeAgent(
            node_id="worker:lenovo",
            relay_host=host,
            relay_port=port,
            ca_file=s["ca_file"],
            certificate_file=s["node_cert"],
            private_key_file=s["node_key"],
            gateway=s["gateway"],
        ) as node:
            _wait(lambda: hub.is_registered("worker:lenovo"))
            coordinator = RelayCoordinatorClient(
                coordinator_id="coordinator",
                relay_host=host,
                relay_port=port,
                ca_file=s["ca_file"],
                certificate_file=s["coord_cert"],
                private_key_file=s["coord_key"],
            )
            remote = RemoteWorkerClient(
                sender_id="coordinator",
                worker_id="worker:lenovo",
                protocol=s["coord_protocol"],
                send=coordinator.send,
            )
            result = remote.call("node_describe", {})
            assert result.ok is True
            assert result.payload["node_id"] == "worker:lenovo"
            assert result.payload["transport"] == "outbound-relay"
            assert result.payload["arbitrary_shell"] is False
            assert node.local_listen_port is None


def test_relay_rejects_registration_when_mtls_cn_does_not_match_node_id(tmp_path: Path):
    s = _stack(tmp_path)
    with RelayHubServer(
        host="127.0.0.1",
        port=0,
        ca_file=s["ca_file"],
        certificate_file=s["relay_cert"],
        private_key_file=s["relay_key"],
        allowed_node_ids={"worker:other"},
        allowed_coordinator_ids={"coordinator"},
    ) as hub:
        host, port = hub.address
        agent = RelayNodeAgent(
            node_id="worker:other",
            relay_host=host,
            relay_port=port,
            ca_file=s["ca_file"],
            certificate_file=s["node_cert"],
            private_key_file=s["node_key"],
            gateway=s["gateway"],
            reconnect=False,
        )
        agent.start()
        _wait(lambda: agent.last_error is not None)
        agent.close()
        assert not hub.is_registered("worker:other")
        assert "identity" in str(agent.last_error).lower() or "common" in str(agent.last_error).lower()


def test_duplicate_node_connection_fences_old_session(tmp_path: Path):
    s = _stack(tmp_path)
    with RelayHubServer(
        host="127.0.0.1",
        port=0,
        ca_file=s["ca_file"],
        certificate_file=s["relay_cert"],
        private_key_file=s["relay_key"],
        allowed_node_ids={"worker:lenovo"},
        allowed_coordinator_ids={"coordinator"},
    ) as hub:
        host, port = hub.address
        first = RelayNodeAgent(
            node_id="worker:lenovo", relay_host=host, relay_port=port,
            ca_file=s["ca_file"], certificate_file=s["node_cert"], private_key_file=s["node_key"],
            gateway=s["gateway"], reconnect=False,
        ).start()
        _wait(lambda: hub.session_generation("worker:lenovo") == 1)
        second = RelayNodeAgent(
            node_id="worker:lenovo", relay_host=host, relay_port=port,
            ca_file=s["ca_file"], certificate_file=s["node_cert"], private_key_file=s["node_key"],
            gateway=s["gateway"], reconnect=False,
        ).start()
        _wait(lambda: hub.session_generation("worker:lenovo") == 2)
        _wait(lambda: first.disconnected)
        assert hub.is_registered("worker:lenovo")
        second.close(); first.close()


def test_unknown_node_call_fails_closed(tmp_path: Path):
    s = _stack(tmp_path)
    with RelayHubServer(
        host="127.0.0.1", port=0, ca_file=s["ca_file"],
        certificate_file=s["relay_cert"], private_key_file=s["relay_key"],
        allowed_node_ids={"worker:lenovo"}, allowed_coordinator_ids={"coordinator"},
    ) as hub:
        host, port = hub.address
        coordinator = RelayCoordinatorClient(
            coordinator_id="coordinator", relay_host=host, relay_port=port,
            ca_file=s["ca_file"], certificate_file=s["coord_cert"], private_key_file=s["coord_key"],
        )
        remote = RemoteWorkerClient(
            sender_id="coordinator", worker_id="worker:lenovo",
            protocol=s["coord_protocol"], send=coordinator.send,
        )
        with pytest.raises(RuntimeError, match="not registered"):
            remote.call("node_describe", {})
