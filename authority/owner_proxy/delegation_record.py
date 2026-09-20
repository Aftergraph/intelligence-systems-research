"""The DelegationRecord: schema, canonical serialization, and ``delegation_ref``.

Spec §3, §4. The record is the SINGLE SOURCE OF TRUTH for the mandate's own
terms (scope allowlist, reserved-matters list, budget ceiling, expiry). The
spine reads those terms ONLY from the verified record, never from a mutable
config file -- otherwise the agent could shrink the fence by editing a file.

``delegation_ref`` is the content address of the record. It reuses the exact
repo-wide canonicalization from ADR-008 (``delegation.token_exchange``: sorted
keys, no-whitespace separators, ensure_ascii=False, UTF-8, sha256) so the ref is
byte-consistent with the rest of the normative-authority stack. Any edit to the
record changes ``delegation_ref`` and invalidates the owner's detached signature
(see ``signature.py`` / spec §8 ``record_tampered``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any

# Bind to ADR-008's canonical hasher rather than reinventing one (spec §2:
# "continuation ... not a parallel scheme"). This is the same function the
# mission-delegation token chain uses for constraints_hash.
from delegation.token_exchange import canonical_constraints_hash

RECORD_SCHEMA = "aftergraph.owner-proxy-delegation/0.1"

# Fields the spine requires to be present and well-formed before it will even
# consider the record. The signature layer proves these were chosen by the
# owner; this layer only checks they exist.
REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "principal",
    "delegate",
    "scope",
    "reserved_matters",
    "budget_ceiling_usd",
    "expires_at",
)


def delegation_ref(record: dict[str, Any]) -> str:
    """Content address of a DelegationRecord: sha256 of its canonical form.

    Uses ADR-008 canonicalization verbatim, so the ref is stable across
    platforms and independent of dict insertion order.
    """
    return canonical_constraints_hash(record)


def validate_structure(record: dict[str, Any]) -> list[str]:
    """Return a list of structural defects (empty == well-formed).

    This is NOT signature verification; it only checks that the fields the
    mandate evaluator and sign_gate depend on are present and of the right
    shape. A record that passes here but fails the signature check is still
    refused -- the signature is the root of trust (spec §1, decision 2).
    """
    defects: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            defects.append(f"record_field_missing:{field}")
    if record.get("schema_version") != RECORD_SCHEMA:
        defects.append("record_schema_invalid")
    scope = record.get("scope")
    if not isinstance(scope, list) or not scope:
        # fail-closed: an empty or absent scope grants nothing (mirrors
        # token_exchange.issue_mission_token refusing an empty scope_allowed).
        defects.append("record_scope_empty")
    reserved = record.get("reserved_matters")
    if not isinstance(reserved, list):
        defects.append("record_reserved_matters_invalid")
    ceiling = record.get("budget_ceiling_usd")
    if not isinstance(ceiling, (int, float)) or isinstance(ceiling, bool) or ceiling <= 0:
        defects.append("record_budget_ceiling_invalid")
    if "not_before" in record and not isinstance(record["not_before"], str):
        defects.append("record_not_before_invalid")
    if "expires_at" in record and not isinstance(record["expires_at"], str):
        defects.append("record_expires_at_invalid")
    return defects


@dataclass(frozen=True)
class DelegationRecord:
    """A parsed, structurally-valid DelegationRecord plus its content address."""

    raw: dict[str, Any]
    ref: str

    @property
    def principal(self) -> str:
        return str(self.raw.get("principal", ""))

    @property
    def delegate(self) -> str:
        return str(self.raw.get("delegate", ""))

    @property
    def scope(self) -> list[str]:
        return list(self.raw.get("scope", []))

    @property
    def reserved_matters(self) -> list[str]:
        return list(self.raw.get("reserved_matters", []))

    @property
    def budget_ceiling_usd(self) -> float:
        return float(self.raw.get("budget_ceiling_usd", 0))


def load_record(path: Path | str) -> DelegationRecord:
    """Read a DelegationRecord from disk and compute its ref.

    Raises ValueError on unreadable/invalid JSON or structural defects; the
    caller (sign_gate) treats any raise as a fail-closed refusal.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    defects = validate_structure(data)
    if defects:
        raise ValueError("delegation_record_invalid:" + ",".join(defects))
    return DelegationRecord(raw=data, ref=delegation_ref(data))