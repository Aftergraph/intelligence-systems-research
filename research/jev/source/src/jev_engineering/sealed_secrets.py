from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

_ALLOWED = {"TYPESAFE_API_KEY", "DIALAGRAM_API_KEY"}


def _fp(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True, slots=True)
class SealedSecretBundle:
    key_fingerprint_sha256: str
    ciphertexts: Mapping[str, str]
    schema: str = "aftergraph.runner-sealed-secrets/1.0"

    def to_dict(self) -> dict[str, object]:
        return {"schema": self.schema, "key_fingerprint_sha256": self.key_fingerprint_sha256, "ciphertexts": dict(self.ciphertexts)}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "SealedSecretBundle":
        if value.get("schema") != "aftergraph.runner-sealed-secrets/1.0":
            raise ValueError("unsupported sealed-secret schema")
        raw = value.get("ciphertexts")
        if not isinstance(raw, Mapping):
            raise ValueError("ciphertexts must be an object")
        ciphertexts = {str(k): str(v) for k, v in raw.items()}
        if set(ciphertexts) - _ALLOWED:
            raise ValueError("sealed bundle contains non-allowlisted secret")
        return cls(str(value.get("key_fingerprint_sha256", "")), ciphertexts)


def generate_runner_seal_keypair() -> tuple[bytes, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private = key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return private, public


def public_key_b64_from_private(private_der: bytes) -> str:
    key = serialization.load_der_private_key(private_der, password=None)
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return base64.b64encode(public).decode("ascii")


def seal_values(values: Mapping[str, str], public_key_der_b64: str) -> SealedSecretBundle:
    clean = {str(k): str(v) for k, v in values.items()}
    if set(clean) - _ALLOWED or not clean or any(not v for v in clean.values()):
        raise ValueError("only non-empty allowlisted secrets may be sealed")
    public_der = base64.b64decode(public_key_der_b64, validate=True)
    key = serialization.load_der_public_key(public_der)
    ciphertexts = {}
    for name, value in sorted(clean.items()):
        ct = key.encrypt(value.encode(), padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=name.encode()))
        ciphertexts[name] = base64.b64encode(ct).decode("ascii")
    return SealedSecretBundle(_fp(public_der), ciphertexts)


def unseal_values(bundle: SealedSecretBundle, private_der: bytes) -> dict[str, str]:
    key = serialization.load_der_private_key(private_der, password=None)
    public_der = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    if _fp(public_der) != bundle.key_fingerprint_sha256:
        raise ValueError("sealed bundle key fingerprint mismatch")
    out = {}
    for name, encoded in bundle.ciphertexts.items():
        if name not in _ALLOWED:
            raise ValueError("non-allowlisted secret")
        value = key.decrypt(base64.b64decode(encoded, validate=True), padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=name.encode()))
        out[name] = value.decode()
    return out


def load_bundle(path: str | Path) -> SealedSecretBundle:
    return SealedSecretBundle.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))