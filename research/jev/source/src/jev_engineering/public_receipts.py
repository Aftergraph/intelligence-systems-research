from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
from typing import Any, Mapping
from pathlib import Path


def _crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
    except ImportError as exc:
        raise RuntimeError("Ed25519 receipts require the optional 'identity' dependency") from exc
    return Ed25519PrivateKey, Ed25519PublicKey, Encoding, PublicFormat, PrivateFormat, NoEncryption


def _canonical(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class PublicSignedReceipt:
    payload: dict[str, Any]
    key_id: str
    algorithm: str
    payload_sha256: str
    signature_b64: str


class Ed25519ReceiptSigner:
    def __init__(self, *, key_id: str, private_key: Any) -> None:
        if not key_id.strip():
            raise ValueError("key_id must be non-empty")
        self.key_id = key_id
        self._private_key = private_key

    @classmethod
    def generate(cls, *, key_id: str) -> "Ed25519ReceiptSigner":
        Ed25519PrivateKey, _, _, _, _, _ = _crypto()
        return cls(key_id=key_id, private_key=Ed25519PrivateKey.generate())

    def public_key_bytes(self) -> bytes:
        _, _, Encoding, PublicFormat, _, _ = _crypto()
        return self._private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    def private_key_bytes(self) -> bytes:
        _, _, Encoding, _, PrivateFormat, NoEncryption = _crypto()
        return self._private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())

    def write_private_key(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.private_key_bytes())
        try:
            target.chmod(0o600)
        except OSError:
            pass
        return target

    @classmethod
    def from_private_key_bytes(cls, *, key_id: str, raw: bytes) -> "Ed25519ReceiptSigner":
        Ed25519PrivateKey, _, _, _, _, _ = _crypto()
        return cls(key_id=key_id, private_key=Ed25519PrivateKey.from_private_bytes(bytes(raw)))

    @classmethod
    def load_private_key(cls, *, key_id: str, path: str | Path) -> "Ed25519ReceiptSigner":
        return cls.from_private_key_bytes(key_id=key_id, raw=Path(path).read_bytes())

    def sign(self, payload: Mapping[str, Any]) -> PublicSignedReceipt:
        body = _canonical(payload)
        digest = hashlib.sha256(body).hexdigest()
        message = f"aftergraph.receipt/v1\n{self.key_id}\n{digest}".encode("utf-8")
        signature = self._private_key.sign(message)
        return PublicSignedReceipt(
            payload=dict(payload), key_id=self.key_id, algorithm="Ed25519",
            payload_sha256=digest, signature_b64=base64.b64encode(signature).decode("ascii"),
        )


class Ed25519ReceiptVerifier:
    def __init__(self, public_keys: Mapping[str, bytes]) -> None:
        self._keys = {str(k): bytes(v) for k, v in public_keys.items()}

    def verify(self, receipt: PublicSignedReceipt) -> bool:
        if receipt.algorithm != "Ed25519":
            return False
        raw = self._keys.get(receipt.key_id)
        if raw is None:
            return False
        body = _canonical(receipt.payload)
        digest = hashlib.sha256(body).hexdigest()
        if digest != receipt.payload_sha256:
            return False
        message = f"aftergraph.receipt/v1\n{receipt.key_id}\n{digest}".encode("utf-8")
        _, Ed25519PublicKey, _, _, _, _ = _crypto()
        try:
            Ed25519PublicKey.from_public_bytes(raw).verify(base64.b64decode(receipt.signature_b64), message)
        except Exception:
            return False
        return True
