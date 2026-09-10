"""Synthetic-only target boundary for STUDY-012.

The boundary is intentionally non-networked. It accepts only canonical
`sandbox://study012/<workload-id>` references backed by the frozen workload
manifest and rejects any URI feature that could smuggle an external target.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping
from urllib.parse import unquote, urlsplit


class SafetyBoundaryError(RuntimeError):
    """Fail-closed STUDY-012 safety-boundary violation."""


_EXPECTED_POLICY = {
    "network": "none",
    "credentials": "none",
    "third_party_targets": "forbidden",
    "target_scheme": "sandbox://",
}
_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST = _ROOT / "data" / "study012_workload_manifest.json"


def _known_workload_ids() -> set[str]:
    try:
        manifest = json.loads(_MANIFEST.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyBoundaryError(f"frozen workload manifest unavailable: {exc}") from exc
    if manifest.get("study_id") != "STUDY-012" or manifest.get("experiment_id") != "ICT-EXP-001":
        raise SafetyBoundaryError("frozen workload manifest identity mismatch")
    ids = {str(row.get("workload_id", "")) for row in manifest.get("workloads", [])}
    if not ids or "" in ids:
        raise SafetyBoundaryError("frozen workload manifest contains invalid workload identity")
    return ids


def canonical_sandbox_target(workload_id: str) -> str:
    """Return the only admissible synthetic target for a frozen workload."""
    if workload_id not in _known_workload_ids():
        raise SafetyBoundaryError("unknown STUDY-012 workload")
    return f"sandbox://study012/{workload_id}"


def validate_synthetic_target(target: str) -> str:
    """Validate a sandbox target without DNS, sockets, filesystem, or I/O side effects."""
    try:
        parsed = urlsplit(target)
    except ValueError as exc:
        raise SafetyBoundaryError("malformed sandbox target") from exc
    if parsed.scheme != "sandbox":
        raise SafetyBoundaryError("target scheme must be sandbox://")
    if parsed.username is not None or parsed.password is not None:
        raise SafetyBoundaryError("embedded credentials are forbidden")
    try:
        port = parsed.port
    except ValueError as exc:
        raise SafetyBoundaryError("ports are forbidden") from exc
    if port is not None:
        raise SafetyBoundaryError("ports are forbidden")
    if parsed.hostname != "study012" or parsed.netloc != "study012":
        raise SafetyBoundaryError("sandbox namespace must be study012")
    if parsed.query or parsed.fragment:
        raise SafetyBoundaryError("query and fragment smuggling are forbidden")

    decoded_path = unquote(parsed.path)
    parts = [part for part in decoded_path.split("/") if part]
    if len(parts) != 1 or any(part in {".", ".."} for part in parts):
        raise SafetyBoundaryError("sandbox path traversal or nesting is forbidden")
    workload_id = parts[0]
    if workload_id not in _known_workload_ids():
        raise SafetyBoundaryError("unknown STUDY-012 workload")
    if target != f"sandbox://study012/{workload_id}":
        raise SafetyBoundaryError("target is not canonical")
    return workload_id


def validate_safety_boundary(policy: Mapping[str, str]) -> None:
    """Require the exact synthetic-only containment policy."""
    for key, expected in _EXPECTED_POLICY.items():
        if policy.get(key) != expected:
            raise SafetyBoundaryError(f"{key} must remain {expected}")
    extra = set(policy) - set(_EXPECTED_POLICY)
    if extra:
        raise SafetyBoundaryError(f"unknown safety policy keys: {sorted(extra)}")
