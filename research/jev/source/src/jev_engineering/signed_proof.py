from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .proof_graph import EvidenceClaim
from .proof_replication import ProofDelta, ProofReplicator
from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier, PublicSignedReceipt


@dataclass(frozen=True, slots=True)
class SignedProofDelta:
    receipt: PublicSignedReceipt

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.receipt)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SignedProofDelta":
        return cls(PublicSignedReceipt(
            payload=dict(value["payload"]), key_id=str(value["key_id"]),
            algorithm=str(value["algorithm"]), payload_sha256=str(value["payload_sha256"]),
            signature_b64=str(value["signature_b64"]),
        ))


def _claim_to_dict(claim: EvidenceClaim) -> dict[str, Any]:
    row = asdict(claim)
    row["parent_claim_ids"] = list(claim.parent_claim_ids)
    return row


def _claim_from_dict(row: Mapping[str, Any]) -> EvidenceClaim:
    return EvidenceClaim(
        claim_id=str(row["claim_id"]), subject=str(row["subject"]),
        predicate=str(row["predicate"]), verifier=str(row["verifier"]),
        method=str(row["method"]), verdict=bool(row["verdict"]),
        dependencies={str(k): str(v) for k, v in dict(row.get("dependencies") or {}).items()},
        parent_claim_ids=tuple(str(v) for v in row.get("parent_claim_ids") or []),
        observed_at=float(row.get("observed_at") or 0.0), metadata=dict(row.get("metadata") or {}),
    )


class SignedProofReplicator:
    """Proof replication that authenticates the delta origin before CAS apply."""

    def __init__(
        self,
        replicator: ProofReplicator,
        *,
        signer: Ed25519ReceiptSigner | None = None,
        verifier: Ed25519ReceiptVerifier | None = None,
    ) -> None:
        self.replicator = replicator
        self.signer = signer
        self.verifier = verifier

    def sign(self, delta: ProofDelta) -> SignedProofDelta:
        if self.signer is None:
            raise RuntimeError("proof delta signer not configured")
        payload = {
            "kind": "aftergraph.proof-delta/v1",
            "graph_id": delta.graph_id,
            "base_revision": delta.base_revision,
            "claims": [_claim_to_dict(c) for c in delta.claims],
        }
        return SignedProofDelta(self.signer.sign(payload))

    def verify_and_apply(self, signed: SignedProofDelta, *, expected_signer_key_id: str | None = None) -> int:
        if self.verifier is None or not self.verifier.verify(signed.receipt):
            raise RuntimeError("proof delta signature invalid")
        if expected_signer_key_id is not None and signed.receipt.key_id != expected_signer_key_id:
            raise RuntimeError("proof delta signer mismatch")
        payload = signed.receipt.payload
        if payload.get("kind") != "aftergraph.proof-delta/v1":
            raise RuntimeError("proof delta kind mismatch")
        delta = ProofDelta(
            graph_id=str(payload["graph_id"]), base_revision=int(payload["base_revision"]),
            claims=tuple(_claim_from_dict(v) for v in payload.get("claims") or []),
        )
        return self.replicator.apply(delta)
