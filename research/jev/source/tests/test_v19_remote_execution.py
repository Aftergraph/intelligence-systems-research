import pytest

from jev_engineering.node_transport import InMemoryNodeEndpoint, NodeProtocol
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
from jev_engineering.remote_execution import RemoteExecutionCoordinator, RemoteWorkOrder, make_verification_handler
from jev_engineering.remote_worker import RemoteWorkerClient


def _runtime(handler=None):
    coord = Ed25519ReceiptSigner.generate(key_id="coord")
    worker = Ed25519ReceiptSigner.generate(key_id="worker")
    verifier = Ed25519ReceiptVerifier({"coord": coord.public_key_bytes(), "worker": worker.public_key_bytes()})
    cp = NodeProtocol(signer=coord, verifier=verifier)
    wp = NodeProtocol(signer=worker, verifier=verifier)
    endpoint = InMemoryNodeEndpoint(node_id="worker:1", protocol=wp, handler=handler or make_verification_handler(verifier_name="sentinel:remote"))
    client = RemoteWorkerClient(sender_id="coord:1", worker_id="worker:1", protocol=cp, send=endpoint.handle)
    return RemoteExecutionCoordinator(client)


def _order():
    return RemoteWorkOrder(
        mission_id="m1", node_id="n1", execution_context_id="ctx1",
        lease_id="lease1", fencing_token=3, authority_grant_id="grant1",
        candidate_sha="sha256:abc", operation="verify_candidate",
    )


def test_remote_work_receipt_is_bound_to_fenced_work_order():
    receipt = _runtime().execute(_order())
    assert receipt.passed
    assert receipt.fencing_token == 3
    assert receipt.candidate_sha == "sha256:abc"
    assert receipt.evidence["verifier"] == "sentinel:remote"


def test_remote_execution_rejects_receipt_binding_mismatch():
    order = _order()
    def bad_handler(operation, payload):
        return {
            "work_order_sha256": order.work_order_sha256,
            "node_id": "different",
            "lease_id": order.lease_id,
            "fencing_token": order.fencing_token,
            "candidate_sha": order.candidate_sha,
            "verdict": "PASS",
            "evidence": {},
        }
    with pytest.raises(RuntimeError, match="binding mismatch"):
        _runtime(bad_handler).execute(order)


def test_remote_work_order_rejects_shell_operation():
    with pytest.raises(ValueError, match="shell"):
        RemoteWorkOrder("m","n","ctx","lease",1,"grant","sha","shell.exec")
