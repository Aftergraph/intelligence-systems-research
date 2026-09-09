"""Fail-closed synthetic safety boundary for STUDY-012.

STUDY-012 is an in-process benchmark. Targets are opaque ``sandbox://`` fixture
identifiers, not network endpoints, filesystem locations, or production service
references. This module centralizes the boundary so manifests and execution use
the same validation rules.
"""
from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import unquote, urlsplit

ALLOWED_SANDBOX_NAMESPACES = frozenset(
    {
        "coordination",
        "topology",
        "egress",
        "authority",
        "evidence",
        "revocation",
    }
)

_REQUIRED_SAFETY_BOUNDARY = {
    "network": "none",
    "credentials": "none",
    "third_party_targets": "forbidden",
    "target_scheme": "sandbox://",
}


def assert_safe_target(target: str) -> str:
    """Return ``target`` only when it is an unambiguous synthetic fixture id."""
    if not isinstance(target, str) or not target:
        raise ValueError("synthetic target must be a non-empty string")
    if "\x00" in target or "\\" in target:
        raise ValueError("synthetic target contains forbidden path syntax")

    parsed = urlsplit(target)
    if parsed.scheme != "sandbox":
        raise ValueError("STUDY-012 target must use sandbox:// only")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("sandbox target must not contain credentials")
    if parsed.port is not None:
        raise ValueError("sandbox target must not contain a port")
    if parsed.query or parsed.fragment:
        raise ValueError("sandbox target must not contain query or fragment data")

    namespace = parsed.hostname
    if namespace not in ALLOWED_SANDBOX_NAMESPACES:
        raise ValueError("sandbox target namespace is not an approved synthetic fixture")

    decoded_path = unquote(parsed.path)
    segments = [segment for segment in decoded_path.split("/") if segment]
    if not segments:
        raise ValueError("sandbox target must identify a synthetic fixture resource")
    if any(segment in {".", ".."} for segment in segments):
        raise ValueError("sandbox target path traversal is forbidden")
    if any(":" in segment or "@" in segment for segment in segments):
        raise ValueError("sandbox target path contains ambiguous target syntax")

    return target


def validate_manifest_safety(manifest: Mapping[str, Any]) -> None:
    """Validate the preregistered safety declaration and every scenario target."""
    safety = manifest.get("safety_boundary")
    if not isinstance(safety, Mapping):
        raise ValueError("manifest safety boundary is missing or malformed")

    for field, expected in _REQUIRED_SAFETY_BOUNDARY.items():
        if safety.get(field) != expected:
            raise ValueError(
                f"manifest safety boundary requires {field}={expected!r}"
            )

    scenarios = manifest.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("manifest safety boundary requires scenario targets")

    for item in scenarios:
        if not isinstance(item, Mapping):
            raise ValueError("manifest safety boundary contains malformed scenario")
        try:
            assert_safe_target(item.get("target"))
        except ValueError as exc:
            raise ValueError(f"manifest safety boundary target rejected: {exc}") from exc
