from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import base64
import json
from typing import Any, Mapping


def _crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    except ImportError as exc:
        raise RuntimeError("Ed25519 workload identity requires the optional 'identity' dependency") from exc
    return Ed25519PrivateKey, Ed25519PublicKey, Encoding, PublicFormat


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _canonical(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class WorkloadAssertion:
    version: str
    key_id: str
    principal: str
    audience: str
    execution_context_id: str
    issued_at: str
    expires_at: str
    nonce: str
    signature_b64: str

    def signed_payload(self) -> dict[str, str]:
        data = asdict(self)
        data.pop("signature_b64")
        return data

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "WorkloadAssertion":
        return cls(**{field: str(payload.get(field) or "") for field in (
            "version", "key_id", "principal", "audience", "execution_context_id",
            "issued_at", "expires_at", "nonce", "signature_b64",
        )})


@dataclass(frozen=True, slots=True)
class VerifiedWorkloadIdentity:
    key_id: str
    principal: str
    execution_context_id: str
    audience: str


class Ed25519WorkloadIssuer:
    def __init__(self, *, key_id: str, principal: str, private_key: Any) -> None:
        if not key_id.strip() or not principal.strip():
            raise ValueError("key_id and principal must be non-empty")
        self.key_id = key_id
        self.principal = principal
        self._private_key = private_key

    @classmethod
    def generate(cls, *, key_id: str, principal: str) -> "Ed25519WorkloadIssuer":
        Ed25519PrivateKey, _, _, _ = _crypto()
        return cls(key_id=key_id, principal=principal, private_key=Ed25519PrivateKey.generate())

    def public_key_bytes(self) -> bytes:
        _, _, Encoding, PublicFormat = _crypto()
        return self._private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    def issue(
        self,
        *,
        audience: str,
        execution_context_id: str,
        ttl: timedelta,
        now: datetime,
        nonce: str | None = None,
    ) -> WorkloadAssertion:
        _aware(now, "now")
        if ttl.total_seconds() <= 0:
            raise ValueError("ttl must be positive")
        if not audience.strip() or not execution_context_id.strip():
            raise ValueError("audience and execution_context_id must be non-empty")
        issued = now.astimezone(timezone.utc)
        expires = issued + ttl
        payload = {
            "version": "aftergraph.workload-assertion/v1",
            "key_id": self.key_id,
            "principal": self.principal,
            "audience": audience,
            "execution_context_id": execution_context_id,
            "issued_at": issued.isoformat(),
            "expires_at": expires.isoformat(),
            "nonce": nonce or base64.urlsafe_b64encode(__import__("os").urandom(12)).decode("ascii").rstrip("="),
        }
        signature = self._private_key.sign(_canonical(payload))
        return WorkloadAssertion(signature_b64=base64.b64encode(signature).decode("ascii"), **payload)


class WorkloadIdentityVerifier:
    def __init__(self, public_keys: Mapping[str, bytes]) -> None:
        self._keys = {str(k): bytes(v) for k, v in public_keys.items()}

    def verify(self, assertion: WorkloadAssertion, *, audience: str, now: datetime) -> VerifiedWorkloadIdentity:
        _aware(now, "now")
        if assertion.version != "aftergraph.workload-assertion/v1":
            raise RuntimeError("unsupported workload assertion version")
        if assertion.audience != audience:
            raise RuntimeError("workload assertion audience mismatch")
        try:
            issued = datetime.fromisoformat(assertion.issued_at)
            expires = datetime.fromisoformat(assertion.expires_at)
        except ValueError as exc:
            raise RuntimeError("invalid workload assertion timestamp") from exc
        _aware(issued, "issued_at")
        _aware(expires, "expires_at")
        now_utc = now.astimezone(timezone.utc)
        if now_utc < issued.astimezone(timezone.utc) - timedelta(seconds=30):
            raise RuntimeError("workload assertion not yet valid")
        if now_utc >= expires.astimezone(timezone.utc):
            raise RuntimeError("workload assertion expired")
        raw = self._keys.get(assertion.key_id)
        if raw is None:
            raise RuntimeError("unknown workload identity key")
        _, Ed25519PublicKey, _, _ = _crypto()
        try:
            public_key = Ed25519PublicKey.from_public_bytes(raw)
            public_key.verify(base64.b64decode(assertion.signature_b64), _canonical(assertion.signed_payload()))
        except Exception as exc:
            raise RuntimeError("workload assertion signature invalid") from exc
        return VerifiedWorkloadIdentity(
            key_id=assertion.key_id,
            principal=assertion.principal,
            execution_context_id=assertion.execution_context_id,
            audience=assertion.audience,
        )
