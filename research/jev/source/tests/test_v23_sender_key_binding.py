from __future__ import annotations

from datetime import datetime, timezone

import pytest

from jev_engineering.node_gateway import NodeGateway, OperationRegistry
from jev_engineering.node_transport import NodeProtocol, NodeRequest
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier


def test_gateway_can_bind_claimed_sender_to_application_signing_key():
    good = Ed25519ReceiptSigner.generate(key_id="coord-key")
    evil = Ed25519ReceiptSigner.generate(key_id="other-trusted-key")
    worker = Ed25519ReceiptSigner.generate(key_id="worker-key")
    keys = {
        "coord-key": good.public_key_bytes(),
        "other-trusted-key": evil.public_key_bytes(),
        "worker-key": worker.public_key_bytes(),
    }
    ops = OperationRegistry(); ops.register("ping", lambda ctx: {"ok": True})
    gateway = NodeGateway(
        node_id="worker", protocol=NodeProtocol(signer=worker, verifier=Ed25519ReceiptVerifier(keys)),
        operations=ops, sender_key_bindings={"coordinator": frozenset({"coord-key"})},
    )
    request = NodeRequest(
        request_id="r1", sender="coordinator", recipient="worker", operation="ping", payload={},
        sent_at=datetime.now(timezone.utc).isoformat(), nonce="n1",
    )
    forged = NodeProtocol(signer=evil, verifier=Ed25519ReceiptVerifier(keys)).sign_request(request)
    with pytest.raises(RuntimeError, match="signing key"):
        gateway.handle(forged.to_dict(), peer_certificate=None)

    legitimate = NodeProtocol(signer=good, verifier=Ed25519ReceiptVerifier(keys)).sign_request(
        NodeRequest(
            request_id="r2", sender="coordinator", recipient="worker", operation="ping", payload={},
            sent_at=datetime.now(timezone.utc).isoformat(), nonce="n2",
        )
    )
    response = gateway.handle(legitimate.to_dict(), peer_certificate=None)
    assert response["payload"]["ok"] is True
