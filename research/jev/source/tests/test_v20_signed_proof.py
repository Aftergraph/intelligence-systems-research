from pathlib import Path
import pytest

from jev_engineering.proof_graph import EvidenceClaim
from jev_engineering.proof_replication import ProofReplicator
from jev_engineering.proof_sync import SqliteProofGraphStore
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
from jev_engineering.signed_proof import SignedProofDelta, SignedProofReplicator


def test_signed_proof_delta_authenticates_origin_and_preserves_revision_fence(tmp_path: Path):
    store = SqliteProofGraphStore(tmp_path / "proof.db")
    base = ProofReplicator(store)
    signer = Ed25519ReceiptSigner.generate(key_id="node-a")
    verifier = Ed25519ReceiptVerifier({"node-a": signer.public_key_bytes()})
    signed = SignedProofReplicator(base, signer=signer, verifier=verifier)
    claim = EvidenceClaim.mint(subject="sha256:x", predicate="tests_pass", verifier="v1", method="pytest", verdict=True)
    delta = base.export_delta("g1", base_revision=0, claims=[claim])
    envelope = signed.sign(delta)
    assert signed.verify_and_apply(envelope, expected_signer_key_id="node-a") == 1
    with pytest.raises(RuntimeError, match="revision conflict"):
        signed.verify_and_apply(envelope, expected_signer_key_id="node-a")


def test_signed_proof_delta_rejects_tamper(tmp_path: Path):
    store = SqliteProofGraphStore(tmp_path / "proof.db")
    base = ProofReplicator(store)
    signer = Ed25519ReceiptSigner.generate(key_id="node-a")
    verifier = Ed25519ReceiptVerifier({"node-a": signer.public_key_bytes()})
    helper = SignedProofReplicator(base, signer=signer, verifier=verifier)
    claim = EvidenceClaim.mint(subject="x", predicate="p", verifier="v", method="m", verdict=True)
    envelope = helper.sign(base.export_delta("g", base_revision=0, claims=[claim]))
    data = envelope.to_dict()
    data["payload"]["graph_id"] = "evil"
    with pytest.raises(RuntimeError, match="signature invalid"):
        helper.verify_and_apply(SignedProofDelta.from_dict(data))
