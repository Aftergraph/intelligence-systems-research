from datetime import datetime, timezone

import httpx
import pytest

from jev_engineering.node_transport import (
    HttpNodeTransport,
    InMemoryNodeEndpoint,
    NodeProtocol,
    NodeRequest,
)
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier


def _pair():
    a = Ed25519ReceiptSigner.generate(key_id="a")
    b = Ed25519ReceiptSigner.generate(key_id="b")
    verifier = Ed25519ReceiptVerifier({"a": a.public_key_bytes(), "b": b.public_key_bytes()})
    return NodeProtocol(signer=a, verifier=verifier), NodeProtocol(signer=b, verifier=verifier)


def test_signed_node_protocol_rejects_replay_and_wrong_recipient():
    client, server = _pair()
    endpoint = InMemoryNodeEndpoint(node_id="worker:b", protocol=server, handler=lambda op, p: {"op": op, **p})
    req = NodeRequest("r1", "coord:a", "worker:b", "heartbeat", {"x": 1}, datetime.now(timezone.utc).isoformat(), "n" * 16)
    msg = client.sign_request(req)
    response = endpoint.handle(msg)
    body = client.verify(response, expected_kind="aftergraph.node-response/v1")
    assert body["request_id"] == "r1"
    assert body["payload"]["x"] == 1
    with pytest.raises(RuntimeError, match="replayed"):
        endpoint.handle(msg)


def test_http_transport_requires_tls_except_loopback():
    transport = HttpNodeTransport()
    with pytest.raises(ValueError, match="requires HTTPS"):
        transport._validate_url("http://example.com/node")
    transport._validate_url("http://127.0.0.1:9000/node")
    transport._validate_url("https://example.com/node")


def test_http_transport_posts_and_parses_signed_message_with_mock_transport():
    client_protocol, server_protocol = _pair()
    endpoint = InMemoryNodeEndpoint(
        node_id="worker:b", protocol=server_protocol,
        handler=lambda op, p: {"operation": op, "value": p["value"] + 1},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        from jev_engineering.node_transport import SignedNodeMessage
        incoming = SignedNodeMessage.from_dict(__import__("json").loads(request.content))
        outgoing = endpoint.handle(incoming)
        return httpx.Response(200, json=outgoing.to_dict())

    http = httpx.Client(transport=httpx.MockTransport(handler))
    transport = HttpNodeTransport(client=http)
    req = NodeRequest("r2", "coord:a", "worker:b", "compute", {"value": 4}, datetime.now(timezone.utc).isoformat(), "x" * 16)
    response = transport.post("https://worker.example/aftergraph/v1", client_protocol.sign_request(req))
    body = client_protocol.verify(response, expected_kind="aftergraph.node-response/v1")
    assert body["payload"] == {"operation": "compute", "value": 5}
