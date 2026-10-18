from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
from typing import Mapping, Any


def _canonical(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class SignedReceipt:
    payload: dict[str, Any]
    key_id: str
    algorithm: str
    payload_sha256: str
    signature_hex: str


class ReceiptSigner:
    """HMAC-SHA256 receipt authenticator using runtime-supplied key material.

    This is shared-secret integrity/authenticity, not public-key attestation.
    """

    def __init__(self, *, key_id: str, secret: bytes) -> None:
        if not key_id.strip():
            raise ValueError("key_id must be non-empty")
        if len(secret) < 32:
            raise ValueError("receipt HMAC secret must be at least 32 bytes")
        self.key_id = key_id
        self._secret = bytes(secret)

    def sign(self, payload: Mapping[str, Any]) -> SignedReceipt:
        body = _canonical(payload)
        digest = hashlib.sha256(body).hexdigest()
        message = f"v1\n{self.key_id}\n{digest}".encode("utf-8")
        signature = hmac.new(self._secret, message, hashlib.sha256).hexdigest()
        return SignedReceipt(
            payload=dict(payload),
            key_id=self.key_id,
            algorithm="HMAC-SHA256",
            payload_sha256=digest,
            signature_hex=signature,
        )


class ReceiptVerifier:
    def __init__(self, keys: Mapping[str, bytes]) -> None:
        self._keys = {str(k): bytes(v) for k, v in keys.items()}

    def verify(self, receipt: SignedReceipt) -> bool:
        if receipt.algorithm != "HMAC-SHA256":
            return False
        secret = self._keys.get(receipt.key_id)
        if secret is None or len(secret) < 32:
            return False
        body = _canonical(receipt.payload)
        digest = hashlib.sha256(body).hexdigest()
        if not hmac.compare_digest(digest, receipt.payload_sha256):
            return False
        message = f"v1\n{receipt.key_id}\n{digest}".encode("utf-8")
        expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, receipt.signature_hex)
