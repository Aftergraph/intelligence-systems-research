from datetime import datetime, timedelta, timezone
from pathlib import Path
import ssl
import httpx
import pytest

from jev_engineering.durable_state import SqliteLeaseStore
from jev_engineering.node_gateway import (
    NodeGateway, NodeGatewayServer, OperationRegistry,
    client_mtls_context, server_mtls_context,
)
from jev_engineering.node_transport import HttpNodeTransport, NodeProtocol
from jev_engineering.pki import EphemeralCertificateAuthority
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
from jev_engineering.remote_control import LeaseControlService
from jev_engineering.remote_worker import RemoteWorkerClient


def _protocols():
    coord = Ed25519ReceiptSigner.generate(key_id="coord")
    worker = Ed25519ReceiptSigner.generate(key_id="worker")
    keys = {"coord": coord.public_key_bytes(), "worker": worker.public_key_bytes()}
    return NodeProtocol(signer=coord, verifier=Ed25519ReceiptVerifier(keys)), NodeProtocol(signer=worker, verifier=Ed25519ReceiptVerifier(keys))


def test_real_loopback_http_transport_executes_signed_bounded_operation():
    coord_protocol, worker_protocol = _protocols()
    ops = OperationRegistry()
    ops.register("echo", lambda ctx: {"sender": ctx.request.sender, "value": ctx.request.payload["value"]})
    gateway = NodeGateway(node_id="worker", protocol=worker_protocol, operations=ops)
    with NodeGatewayServer(gateway=gateway) as server:
        host, port = server.address
        transport = HttpNodeTransport()
        client = RemoteWorkerClient(
            sender_id="coord", worker_id="worker", protocol=coord_protocol,
            send=lambda message: transport.post(f"http://{host}:{port}/v1/node/call", message),
        )
        result = client.call("echo", {"value": 7})
        assert result.ok is True
        assert result.payload == {"sender": "coord", "value": 7}


def test_mtls_gateway_requires_client_certificate_and_verifies_signed_protocol(tmp_path: Path):
    ca = EphemeralCertificateAuthority()
    server_id = ca.issue(common_name="localhost", dns_names=["localhost"], ip_addresses=["127.0.0.1"], server=True)
    client_id = ca.issue(common_name="coord", client=True)
    s_cert, s_key, ca_file = server_id.write(tmp_path / "server", prefix="server")
    c_cert, c_key, _ = client_id.write(tmp_path / "client", prefix="client")
    coord_protocol, worker_protocol = _protocols()
    ops = OperationRegistry(); ops.register("echo", lambda ctx: {"peer_cert": bool(ctx.peer_certificate)})
    gateway = NodeGateway(node_id="worker", protocol=worker_protocol, operations=ops)
    ssl_ctx = server_mtls_context(ca_file=str(ca_file), certificate_file=str(s_cert), private_key_file=str(s_key))
    with NodeGatewayServer(gateway=gateway, ssl_context=ssl_ctx) as server:
        _, port = server.address
        client_ctx = client_mtls_context(ca_file=str(ca_file), certificate_file=str(c_cert), private_key_file=str(c_key))
        with httpx.Client(verify=client_ctx, timeout=5) as http:
            transport = HttpNodeTransport(client=http)
            client = RemoteWorkerClient(
                sender_id="coord", worker_id="worker", protocol=coord_protocol,
                send=lambda message: transport.post(f"https://localhost:{port}/v1/node/call", message),
            )
            result = client.call("echo", {})
            assert result.ok is True and result.payload["peer_cert"] is True
        # CA trust without a client cert must fail TLS handshake.
        no_client_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=str(ca_file))
        with httpx.Client(verify=no_client_ctx, timeout=3) as http:
            with pytest.raises(httpx.TransportError):
                http.get(f"https://localhost:{port}/healthz")


def test_remote_lease_heartbeat_is_sender_bound_and_fenced(tmp_path: Path):
    coord_protocol, worker_protocol = _protocols()
    leases = SqliteLeaseStore(tmp_path / "lease.db")
    now = datetime.now(timezone.utc)
    lease = leases.issue(node_id="n1", worker_id="coord", authority_grant_id="g1", capabilities={"verify"}, ttl=timedelta(minutes=2), now=now)
    ops = OperationRegistry(); LeaseControlService(leases).register(ops)
    gateway = NodeGateway(node_id="worker", protocol=worker_protocol, operations=ops)
    with NodeGatewayServer(gateway=gateway) as server:
        host, port = server.address
        transport = HttpNodeTransport()
        client = RemoteWorkerClient(sender_id="coord", worker_id="worker", protocol=coord_protocol, send=lambda m: transport.post(f"http://{host}:{port}/v1/node/call", m))
        result = client.call("lease_heartbeat", {"lease_id": lease.lease_id, "fencing_token": lease.fencing_token})
        assert result.ok is True
        leases.issue(node_id="n1", worker_id="other", authority_grant_id="g1", capabilities={"verify"}, ttl=timedelta(minutes=2), now=datetime.now(timezone.utc))
        result = client.call("lease_heartbeat", {"lease_id": lease.lease_id, "fencing_token": lease.fencing_token})
        assert result.ok is False
        assert "fenced" in result.payload["message"]

def test_mtls_peer_cn_is_bound_to_signed_sender(tmp_path: Path):
    ca = EphemeralCertificateAuthority()
    server_id = ca.issue(common_name="localhost", dns_names=["localhost"], server=True)
    # TLS identity says someone-else, while signed request claims coord.
    client_id = ca.issue(common_name="someone-else", client=True)
    s_cert, s_key, ca_file = server_id.write(tmp_path / "server2", prefix="server")
    c_cert, c_key, _ = client_id.write(tmp_path / "client2", prefix="client")
    coord_protocol, worker_protocol = _protocols()
    ops = OperationRegistry(); ops.register("echo", lambda ctx: {"ok": True})
    gateway = NodeGateway(node_id="worker", protocol=worker_protocol, operations=ops)
    ssl_ctx = server_mtls_context(ca_file=str(ca_file), certificate_file=str(s_cert), private_key_file=str(s_key))
    with NodeGatewayServer(gateway=gateway, ssl_context=ssl_ctx) as server:
        _, port = server.address
        client_ctx = client_mtls_context(ca_file=str(ca_file), certificate_file=str(c_cert), private_key_file=str(c_key))
        with httpx.Client(verify=client_ctx, timeout=5) as http:
            transport = HttpNodeTransport(client=http)
            client = RemoteWorkerClient(sender_id="coord", worker_id="worker", protocol=coord_protocol, send=lambda m: transport.post(f"https://localhost:{port}/v1/node/call", m))
            with pytest.raises(httpx.HTTPStatusError):
                client.call("echo", {})
