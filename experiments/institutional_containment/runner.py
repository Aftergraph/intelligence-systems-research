"""Deterministic execution boundary for STUDY-012.

The runner is intentionally synthetic and in-process. It fails closed on any
request to substitute or fall back to another execution mode so confirmatory
records cannot be silently replaced by simulation or another backend.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any, Mapping

from .harness import CONDITIONS, run_scenario
from .safety import assert_safe_target, validate_manifest_safety
from .scenarios import SCENARIOS

EXECUTION_ENGINE = "synthetic_in_process_v1"
EXECUTION_CLASS = "SYNTHETIC_VALID"
DEFAULT_MANIFEST = Path("data/study012_scenario_manifest.json")


def manifest_digest(path: Path | str) -> str:
    """Return the SHA-256 of the exact manifest bytes used for a run."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical_digest(manifest: Mapping[str, Any]) -> str:
    payload = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_manifest(
    *,
    manifest_path: Path | str | None,
    manifest: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    if manifest_path is not None and manifest is not None:
        raise ValueError("provide manifest_path or manifest, not both")

    if manifest is not None:
        loaded = dict(manifest)
        digest = _canonical_digest(loaded)
    else:
        path = Path(manifest_path or DEFAULT_MANIFEST)
        loaded = json.loads(path.read_text(encoding="utf-8"))
        digest = manifest_digest(path)

    if loaded.get("study_id") != "STUDY-012":
        raise ValueError("manifest must declare study_id STUDY-012")
    if loaded.get("experiment_id") != "ICT-EXP-0001":
        raise ValueError("manifest must declare experiment_id ICT-EXP-0001")

    declared_conditions = tuple(loaded.get("conditions", ()))
    if declared_conditions != CONDITIONS:
        raise ValueError("manifest condition ladder does not match STUDY-012")

    declared_scenarios = loaded.get("scenarios", ())
    declared_ids = tuple(item.get("scenario_id") for item in declared_scenarios)
    canonical_ids = tuple(scenario.scenario_id for scenario in SCENARIOS)
    if declared_ids != canonical_ids:
        raise ValueError("manifest scenario set/order does not match STUDY-012")

    validate_manifest_safety(loaded)

    declared_targets = tuple(item.get("target") for item in declared_scenarios)
    canonical_targets = tuple(scenario.synthetic_target for scenario in SCENARIOS)
    if declared_targets != canonical_targets:
        raise ValueError("manifest scenario target set/order does not match STUDY-012")

    return loaded, digest


def run_condition(
    condition: str,
    *,
    manifest_path: Path | str | None = None,
    manifest: Mapping[str, Any] | None = None,
    seed: int,
    fallback_mode: str | None = None,
) -> list[dict[str, Any]]:
    """Execute one STUDY-012 condition and return deterministic raw records.

    ``fallback_mode`` exists only to make the no-substitution invariant explicit:
    any non-null value is rejected rather than interpreted.
    """
    if fallback_mode is not None:
        raise ValueError("fallback or substituted execution is forbidden in STUDY-012")
    if condition not in CONDITIONS:
        raise ValueError(f"unknown STUDY-012 condition: {condition}")

    _manifest, digest = _load_manifest(
        manifest_path=manifest_path,
        manifest=manifest,
    )

    ordered = list(SCENARIOS)
    random.Random(seed).shuffle(ordered)

    records: list[dict[str, Any]] = []
    for ordinal, scenario in enumerate(ordered):
        # Defense in depth: a future code change to the canonical scenario table
        # cannot bypass the same synthetic target validator used for manifests.
        assert_safe_target(scenario.synthetic_target)
        event = run_scenario(condition, scenario)
        records.append(
            {
                "study_id": "STUDY-012",
                "experiment_id": "ICT-EXP-0001",
                "run_id": f"ICT-EXP-0001:{condition}:{seed}:{ordinal}:{scenario.scenario_id}",
                "condition": condition,
                "seed": seed,
                "scenario_id": scenario.scenario_id,
                "failure_class": scenario.failure_class,
                "synthetic_target": scenario.synthetic_target,
                "execution_engine": EXECUTION_ENGINE,
                "execution_class": EXECUTION_CLASS,
                "fallback_used": False,
                "manifest_sha256": digest,
                "attempted": event.attempted,
                "blocked": event.blocked,
                "violation_occurred": event.violation_occurred,
                "transcript_claimed_success": event.transcript_claimed_success,
                "evidence_detected_violation": event.evidence_detected_violation,
            }
        )

    return records


def run_workload_matrix(
    *,
    manifest_path: Path | str,
    replicate_id: str,
    seed: int,
    source_commit: str,
) -> list[dict[str, Any]]:
    """Execute the frozen paired workload matrix. Not implemented yet."""
    raise NotImplementedError("STUDY-012 paired workload runner not implemented")
