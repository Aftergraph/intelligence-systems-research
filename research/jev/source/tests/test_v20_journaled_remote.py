from jev_engineering.node_transport import InMemoryNodeEndpoint, NodeProtocol
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
from jev_engineering.remote_execution import (
    RemoteExecutionCoordinator, RemoteWorkOrder, make_journaled_verification_handler,
    validate_execution_journal,
)
from jev_engineering.remote_worker import RemoteWorkerClient


def test_journaled_remote_verification_binds_trajectory():
    coord = Ed25519ReceiptSigner.generate(key_id="coord")
    worker = Ed25519ReceiptSigner.generate(key_id="worker")
    keys = {"coord": coord.public_key_bytes(), "worker": worker.public_key_bytes()}
    cp = NodeProtocol(signer=coord, verifier=Ed25519ReceiptVerifier(keys))
    wp = NodeProtocol(signer=worker, verifier=Ed25519ReceiptVerifier(keys))
    endpoint = InMemoryNodeEndpoint(node_id="worker", protocol=wp, handler=make_journaled_verification_handler(verifier_name="sentinel"))
    client = RemoteWorkerClient(sender_id="coord", worker_id="worker", protocol=cp, send=endpoint.handle)
    receipt = RemoteExecutionCoordinator(client).execute(RemoteWorkOrder(
        mission_id="m", node_id="n", execution_context_id="ctx", lease_id="lease", fencing_token=1,
        authority_grant_id="g", candidate_sha="sha256:x",
    ))
    head = validate_execution_journal(receipt)
    assert head and len(receipt.evidence["execution_events"]) == 2
