"""Owner approval gate for STUDY-015 confirmatory execution."""
from __future__ import annotations

from typing import Any


class OwnerGateError(ValueError):
    pass


def assert_owner_approved(gate: dict[str, Any]) -> None:
    if gate.get("status") != "APPROVED":
        raise OwnerGateError("owner gate status is not APPROVED")
    if gate.get("authorize_confirmatory_execution") is not True:
        raise OwnerGateError("confirmatory execution is not authorized")
    if not gate.get("approved_by"):
        raise OwnerGateError("approved_by is required")
    if not gate.get("approved_at"):
        raise OwnerGateError("approved_at is required")
    protocol_hash = str(gate.get("protocol_sha256") or "")
    if len(protocol_hash) != 64 or any(ch not in "0123456789abcdef" for ch in protocol_hash):
        raise OwnerGateError("valid protocol_sha256 is required")
