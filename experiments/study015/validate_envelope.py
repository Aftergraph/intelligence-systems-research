"""Validation for STUDY-015 System Performance Envelopes.

Schema validation handles structure. Semantic validation handles cross-field
invariants that should not be weakened by a permissive producer.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = ROOT / "data" / "study015_performance_envelope.schema.json"


class Study015EnvelopeError(ValueError):
    """Raised when a STUDY-015 envelope violates a semantic invariant."""


def load_schema(path: Path = DEFAULT_SCHEMA) -> dict[str, Any]:
    schema = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    return schema


def _semantic_errors(envelope: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    outcome = envelope["outcome"]
    verification = envelope["verification"]
    performance = envelope["performance"]
    authority = envelope["authority"]

    execution_class = envelope["execution_class"]
    is_live = envelope["is_live"]
    if execution_class == "DRY_RUN" and is_live:
        errors.append("DRY_RUN must have is_live=false")
    if execution_class in {"LIVE_VALID", "LIVE_PROVIDER_FAILURE", "LIVE_PROTOCOL_FAILURE"} and not is_live:
        errors.append(f"{execution_class} must have is_live=true")

    if outcome["verified_success"]:
        if not verification["independent"]:
            errors.append("verified_success requires independent verification")
        if verification["verdict"] != "PASS":
            errors.append("verified_success requires verification verdict PASS")
        if not verification.get("verification_subject"):
            errors.append("verified_success requires verification_subject")
        if not verification.get("evidence_root"):
            errors.append("verified_success requires evidence_root")
        if performance.get("time_to_verified_ms") is None:
            errors.append("verified_success requires time_to_verified_ms")

    if outcome["false_completion"]:
        if not outcome["declared_complete"]:
            errors.append("false_completion requires declared_complete")
        if outcome["verified_success"]:
            errors.append("false_completion cannot also be verified_success")

    if outcome["abstained"]:
        if outcome["declared_complete"]:
            errors.append("abstained cannot also be declared_complete")
        if outcome["verified_success"]:
            errors.append("abstained cannot also be verified_success")

    if performance["control_plane_tokens"] > performance["tokens_total"]:
        errors.append("control_plane_tokens cannot exceed tokens_total")

    if authority["revoked_or_stale_effect_succeeded"] and not outcome["unauthorized_action"]:
        errors.append(
            "successful effect under revoked/stale authority must be marked unauthorized_action"
        )

    if envelope["condition"] == "FULL_MINUS":
        variant = envelope.get("condition_variant")
        if not isinstance(variant, str) or not variant.strip():
            errors.append("FULL_MINUS requires a non-empty condition_variant")

    return errors


def validate_envelope(
    envelope: dict[str, Any],
    *,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_schema = schema if schema is not None else load_schema()
    jsonschema.validate(instance=envelope, schema=active_schema)
    errors = _semantic_errors(envelope)
    if errors:
        raise Study015EnvelopeError("; ".join(errors))
    return envelope


def validate_file(path: Path, *, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    return validate_envelope(envelope, schema=schema)
