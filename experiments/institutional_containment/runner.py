"""Fail-closed execution admission for STUDY-012 / ICT-EXP-0001.

G12-4 exists to make execution substitution explicit. This module does not run
confirmatory workloads; it validates the declared execution seam before any
future runner may do so.

Experiment identity is resolved through the G12-9 registry alignment record:
the canonical ID is ICT-EXP-0001, and the frozen v1.0.0 manifest's ICT-EXP-001
is admitted only as a declared historical alias.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ExecutionContractError(RuntimeError):
    """Raised when an execution request cannot be admitted exactly as declared."""


_ALLOWED_PRECONFIRMATORY_CLASS = "SYNTHETIC_CONFORMANCE_VALID"
_EXPECTED_STUDY = "STUDY-012"
_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "study012_registry_alignment.json"


def _load_registry() -> dict[str, Any]:
    return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))


def _admitted_experiment_ids(registry: dict[str, Any]) -> set[str]:
    """Return the set of experiment IDs that may appear in a frozen manifest."""
    ids = {registry["canonical_experiment_id"]}
    for alias in registry.get("non_canonical_aliases", []):
        ids.add(alias["experiment_id"])
    return ids


def prepare_execution(
    *,
    manifest_path: Path | str,
    declared_manifest_sha256: str,
    requested_engine: str,
    actual_engine: str,
    execution_class: str,
    fallback_mode: str | None,
    confirmatory: bool,
) -> dict[str, Any]:
    """Validate an exact execution declaration and return an admission receipt.

    No fallback is permitted. Pre-confirmatory synthetic execution can be
    admitted only when requested and actual engines match exactly. Confirmatory
    execution remains unavailable through this synthetic boundary.
    """
    if fallback_mode is not None:
        raise ExecutionContractError("fallback substitution is forbidden")
    if not requested_engine or not actual_engine or requested_engine != actual_engine:
        raise ExecutionContractError("engine substitution is forbidden")
    if execution_class != _ALLOWED_PRECONFIRMATORY_CLASS:
        raise ExecutionContractError("execution class is not admitted")
    if confirmatory:
        raise ExecutionContractError(
            "confirmatory execution cannot use the synthetic pre-confirmatory engine"
        )

    path = Path(manifest_path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ExecutionContractError(f"manifest unavailable: {exc}") from exc
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != declared_manifest_sha256.lower():
        raise ExecutionContractError("manifest substitution or hash drift detected")

    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExecutionContractError("manifest is not valid JSON") from exc

    registry = _load_registry()
    admitted = _admitted_experiment_ids(registry)
    canonical = registry["canonical_experiment_id"]

    if manifest.get("study_id") != _EXPECTED_STUDY:
        raise ExecutionContractError("manifest study identity mismatch")
    if manifest.get("experiment_id") not in admitted:
        raise ExecutionContractError(
            f"manifest experiment identity mismatch: {manifest.get('experiment_id')} "
            f"not in admitted set {admitted}"
        )
    if manifest.get("freeze_version") != "v1.0.0":
        raise ExecutionContractError("manifest is not at frozen workload version v1.0.0")
    if not manifest.get("root_hash") or not manifest.get("workloads"):
        raise ExecutionContractError("manifest lacks frozen workload identity")

    return {
        "study_id": _EXPECTED_STUDY,
        "experiment_id": manifest["experiment_id"],
        "canonical_experiment_id": canonical,
        "manifest_sha256": actual_sha,
        "manifest_root_hash": manifest["root_hash"],
        "requested_engine": requested_engine,
        "actual_engine": actual_engine,
        "execution_class": execution_class,
        "fallback_used": False,
        "confirmatory_eligible": False,
        "workload_count": len(manifest["workloads"]),
    }
