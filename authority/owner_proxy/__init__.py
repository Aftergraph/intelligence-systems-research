"""Owner-authority proxy spine (spec: docs/superpowers/specs/2026-09-20-owner-authority-agent-design.md).

A standing, revocable, hardware-rooted proxy that lets the owner's instrument
SIGN gates with truthful provenance while making it mechanically impossible for
any agent to MINT the owner's authority.

This is a continuation of the repo's normative-authority line, not a parallel
scheme: canonical hashing reuses ``delegation.token_exchange`` (ADR-008), and
the temporal/scope/attenuation semantics mirror ``authority.evaluator`` and
``authority.delegation`` (Invariant 3). The forgery-resistance lives in the
detached GPG signature over the DelegationRecord (verified here, never minted
here); the persona "face" (the owner-authority skill) holds zero authority.
"""

from .delegation_record import (
    RECORD_SCHEMA,
    DelegationRecord,
    delegation_ref,
    load_record,
    validate_structure,
)
from .mandate import (
    ACTION_MATTER,
    ALLOW_ROUTINE,
    REFUSE_INVALID,
    REFUSE_RESERVED,
    MandateDecision,
    evaluate_mandate,
)
from .revocation import RevocationSet, load_revocations, revoked_refs
from .signature import SignatureResult, verify_detached_signature
from .ledger import LedgerResult, append_entry, head_seq, verify_chain
from .sign_gate import SignGateResult, build_approval_record, sign_calibration_gate

__all__ = [
    "RECORD_SCHEMA",
    "DelegationRecord",
    "delegation_ref",
    "load_record",
    "validate_structure",
    "ACTION_MATTER",
    "ALLOW_ROUTINE",
    "REFUSE_INVALID",
    "REFUSE_RESERVED",
    "MandateDecision",
    "evaluate_mandate",
    "RevocationSet",
    "load_revocations",
    "revoked_refs",
    "SignatureResult",
    "verify_detached_signature",
    "LedgerResult",
    "append_entry",
    "head_seq",
    "verify_chain",
    "SignGateResult",
    "build_approval_record",
    "sign_calibration_gate",
]