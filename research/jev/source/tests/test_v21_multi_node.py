from pathlib import Path

import pytest

from jev_engineering.multi_node import MultiNodeVerificationCoordinator, RemoteVerifierTarget
from jev_engineering.node_transport import InMemoryNodeEndpoint, NodeProtocol
from jev_engineering.proof_sync import SqliteProofGraphStore
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
from jev_engineering.remote_execution import make_journaled_verification_handler
from jev_engineering.remote_worker import RemoteWorkerClient


def _client(coord, worker, worker_id):
    keys = {"coord": coord.public_key_bytes(), worker_id: worker.public_key_bytes()}
    cp = NodeProtocol(signer=coord, verifier=Ed25519ReceiptVerifier(keys))
    wp = NodeProtocol(signer=worker, verifier=Ed25519ReceiptVerifier(keys))
    endpoint = InMemoryNodeEndpoint(
        node_id=worker_id, protocol=wp,
        handler=make_journaled_verification_handler(verifier_name=worker_id),
    )
    return RemoteWorkerClient(sender_id="coord", worker_id=worker_id, protocol=cp, send=endpoint.handle)


def test_multi_node_requires_independent_domains_and_accepts_quorum(tmp_path: Path):
    coord = Ed25519ReceiptSigner.generate(key_id="coord")
    wa = Ed25519ReceiptSigner.generate(key_id="wa")
    wb = Ed25519ReceiptSigner.generate(key_id="wb")
    ca = _client(coord, wa, "wa")
    cb = _client(coord, wb, "wb")
    store = SqliteProofGraphStore(tmp_path / "proof.db")
    runtime = MultiNodeVerificationCoordinator(store=store, graph_id="g", min_trust_domains=2)
    result = runtime.verify(
        mission_id="m", node_id="n", execution_context_id="ctx", candidate_sha="sha256:x",
        targets=[
            RemoteVerifierTarget("wa", "lenovo", ca, "la", 1, "ga"),
            RemoteVerifierTarget("wb", "vds", cb, "lb", 1, "gb"),
        ],
    )
    assert result.accepted
    assert set(result.positive_trust_domains) == {"lenovo", "vds"}
    assert result.receipts == 2


def test_multi_node_rejects_same_trust_domain(tmp_path: Path):
    coord = Ed25519ReceiptSigner.generate(key_id="coord")
    wa = Ed25519ReceiptSigner.generate(key_id="wa")
    wb = Ed25519ReceiptSigner.generate(key_id="wb")
    runtime = MultiNodeVerificationCoordinator(
        store=SqliteProofGraphStore(tmp_path / "proof.db"), graph_id="g", min_trust_domains=2,
    )
    with pytest.raises(RuntimeError, match="independent trust domains"):
        runtime.verify(
            mission_id="m", node_id="n", execution_context_id="ctx", candidate_sha="sha256:x",
            targets=[
                RemoteVerifierTarget("wa", "same", _client(coord, wa, "wa"), "la", 1, "ga"),
                RemoteVerifierTarget("wb", "same", _client(coord, wb, "wb"), "lb", 1, "gb"),
            ],
        )
