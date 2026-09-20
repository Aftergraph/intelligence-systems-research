"""Revocation: an owner-signed record that poisons a delegation_ref (spec §3, §8).

A revocation is itself a DelegationRecord-adjacent signed object:
``{"schema_version", "revokes_delegation_ref", "revoked_at", "reason"}`` plus a
detached GPG signature verified against the SAME committed owner pubkey. The
spine loads the live revocation set on every act and never caches a pass, so a
revocation takes effect immediately (spec §8: "checked live, never cached").

Cascade semantics match ``authority.delegation.DelegationManager.revoke_subtree``
-- revoking a parent poisons descendants -- but v1 enforces attenuation on
verification only and does not mint sub-delegations (spec §10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import json

from .signature import SignatureResult, verify_detached_signature

REVOCATION_SCHEMA = "aftergraph.owner-proxy-revocation/0.1"


@dataclass(frozen=True)
class RevocationSet:
    # delegation_ref -> earliest revoked_at (ISO) among valid, signature-verified
    # revocations naming that ref.
    poisoned: dict[str, str] = field(default_factory=dict)
    errors: tuple[str, ...] = ()

    def is_revoked(self, delegation_ref: str, now: datetime) -> bool:
        revoked_at = self.poisoned.get(delegation_ref)
        if revoked_at is None:
            return False
        try:
            ts = datetime.fromisoformat(revoked_at.replace("Z", "+00:00"))
        except ValueError:
            # A revocation we cannot time-parse still poisons from load forward;
            # fail-closed rather than fail-open.
            return True
        return now >= ts


def _load_signed_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    record_path = path
    sig_path = path.with_suffix(path.suffix + ".sig") if not path.name.endswith(".sig") else None
    # Convention: revocation_<name>.json + revocation_<name>.json.sig
    if sig_path is None or not sig_path.exists():
        alt = path.parent / (path.stem + ".sig")
        sig_path = alt if alt.exists() else None
    if sig_path is None:
        return None, "revocation_signature_missing"
    try:
        data = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "revocation_invalid_json"
    return (data, str(sig_path)), None


def load_revocations(
    keys_dir: Path | str,
    pubkey_armored: str,
    *,
    gnupghome: Path | str | None = None,
) -> RevocationSet:
    """Verify every ``revocation_*.json`` in ``keys_dir`` and collect poisoned refs.

    A revocation whose signature fails is treated as poison-indeterminate and
    surfaced in ``errors`` -- the caller (sign_gate) fails closed if ANY error is
    present, because an untrusted revocation set cannot certify a mandate clean.
    """
    keys_dir = Path(keys_dir)
    poisoned: dict[str, str] = {}
    errors: list[str] = []
    for path in sorted(keys_dir.glob("revocation_*.json")):
        loaded, err = _load_signed_json(path)
        if err:
            errors.append(f"{path.name}:{err}")
            continue
        data, sig_path = loaded  # type: ignore[misc]
        sig_result: SignatureResult = verify_detached_signature(
            path.read_bytes(), Path(sig_path).read_bytes(), pubkey_armored, gnupghome=gnupghome
        )
        if not sig_result.ok:
            errors.append(f"{path.name}:revocation_{sig_result.reason}")
            continue
        if data.get("schema_version") != REVOCATION_SCHEMA:
            errors.append(f"{path.name}:revocation_schema_invalid")
            continue
        ref = data.get("revokes_delegation_ref")
        at = data.get("revoked_at")
        if not isinstance(ref, str) or not isinstance(at, str):
            errors.append(f"{path.name}:revocation_fields_missing")
            continue
        prev = poisoned.get(ref)
        if prev is None or at < prev:
            poisoned[ref] = at
    return RevocationSet(poisoned=poisoned, errors=tuple(errors))


def revoked_refs(keys_dir: Path | str, pubkey_armored: str, *, gnupghome: Path | str | None = None) -> RevocationSet:
    """Convenience wrapper mirroring the module's public naming."""
    return load_revocations(keys_dir, pubkey_armored, gnupghome=gnupghome)