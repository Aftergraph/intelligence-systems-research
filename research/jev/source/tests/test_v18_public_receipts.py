from __future__ import annotations

from dataclasses import replace

from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier


def test_public_key_receipt_can_be_verified_without_signing_key() -> None:
    signer = Ed25519ReceiptSigner.generate(key_id="verifier-k1")
    receipt = signer.sign({"subject": "sha256:abc", "predicate": "verified", "verdict": True})
    verifier = Ed25519ReceiptVerifier({signer.key_id: signer.public_key_bytes()})
    assert verifier.verify(receipt) is True
    assert verifier.verify(replace(receipt, payload={**receipt.payload, "verdict": False})) is False
