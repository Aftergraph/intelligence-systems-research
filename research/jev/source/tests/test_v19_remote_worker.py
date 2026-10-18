from jev_engineering.node_transport import InMemoryNodeEndpoint, NodeProtocol
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
from jev_engineering.remote_worker import RemoteWorkerClient


def test_remote_worker_uses_signed_bounded_operation():
    coordinator = Ed25519ReceiptSigner.generate(key_id="coord-key")
    worker = Ed25519ReceiptSigner.generate(key_id="worker-key")
    verifier = Ed25519ReceiptVerifier({
        "coord-key": coordinator.public_key_bytes(),
        "worker-key": worker.public_key_bytes(),
    })
    cp = NodeProtocol(signer=coordinator, verifier=verifier)
    wp = NodeProtocol(signer=worker, verifier=verifier)
    endpoint = InMemoryNodeEndpoint(
        node_id="worker:lenovo",
        protocol=wp,
        handler=lambda operation, payload: {"operation": operation, "sha": payload["sha"]},
    )
    client = RemoteWorkerClient(
        sender_id="coordinator:runtime",
        worker_id="worker:lenovo",
        protocol=cp,
        send=endpoint.handle,
    )
    result = client.call("verify_candidate", {"sha": "abc123"})
    assert result.ok is True
    assert result.payload == {"operation": "verify_candidate", "sha": "abc123"}
