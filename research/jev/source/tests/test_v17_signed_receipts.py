from __future__ import annotations

from dataclasses import replace

from jev_engineering.signed_receipts import ReceiptSigner, ReceiptVerifier


def test_hmac_receipt_round_trip_and_tamper_detection() -> None:
    signer = ReceiptSigner(key_id="runtime-k1", secret=b"x" * 32)
    signed = signer.sign({"action_id": "a1", "state": "committed", "subject": "sha256:abc"})
    verifier = ReceiptVerifier({"runtime-k1": b"x" * 32})
    assert verifier.verify(signed) is True
    tampered = replace(signed, payload={**signed.payload, "state": "compensated"})
    assert verifier.verify(tampered) is False


def test_unknown_key_or_wrong_key_fails_closed() -> None:
    signed = ReceiptSigner(key_id="k1", secret=b"a" * 32).sign({"x": 1})
    assert ReceiptVerifier({}).verify(signed) is False
    assert ReceiptVerifier({"k1": b"b" * 32}).verify(signed) is False
