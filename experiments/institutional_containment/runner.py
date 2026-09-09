"""Deterministic execution boundary for STUDY-012.

The runner is intentionally synthetic and in-process. It fails closed on any
request to substitute or fall back to another execution mode so confirmatory
records cannot be silently replaced by simulation or another backend.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any, Mapping

from .harness import CONDITIONS, run_scenario
from .safety import assert_safe_target, validate_manifest_safety
from .scenarios import SCENARIOS

EXECUTION_ENGINE = "synthetic_in_process_v1"
EXECUTION_CLASS = "SYNTHETIC_VALID"
DEFAULT_MANIFEST = Path("data/study012_scenario_manifest.json")
_FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REPLICATE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


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


def _stable_random_seed(*parts: object) -> int:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


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


def _validate_workload_manifest(manifest: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if manifest.get("status") != "FROZEN_WORKLOAD_V1":
        raise ValueError("workload manifest must have status FROZEN_WORKLOAD_V1")
    if manifest.get("runtime_version") != EXECUTION_ENGINE:
        raise ValueError("workload manifest runtime_version does not match runner")
    for field in ("model_id", "mission_contract_version"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"workload manifest requires {field}")

    domains = manifest.get("domains")
    if not isinstance(domains, list) or len(domains) != 3:
        raise ValueError("workload manifest must freeze exactly three domains")

    canonical_ids = tuple(scenario.scenario_id for scenario in SCENARIOS)
    workload_ids: set[str] = set()
    domain_ids: set[str] = set()
    for domain in domains:
        if not isinstance(domain, Mapping):
            raise ValueError("workload manifest contains malformed domain")
        domain_id = domain.get("domain_id")
        workload_id = domain.get("workload_id")
        if not isinstance(domain_id, str) or not domain_id:
            raise ValueError("workload manifest domain_id is required")
        if not isinstance(workload_id, str) or not _REPLICATE_ID_RE.fullmatch(workload_id):
            raise ValueError("workload manifest workload_id is malformed")
        if domain_id in domain_ids or workload_id in workload_ids:
            raise ValueError("workload manifest domain/workload ids must be unique")
        domain_ids.add(domain_id)
        workload_ids.add(workload_id)
        if domain.get("fixture_scheme") != "sandbox://":
            raise ValueError("workload manifest fixture_scheme must be sandbox://")
        if domain.get("ground_truth") != "deterministic_in_process":
            raise ValueError("workload manifest ground_truth must be deterministic_in_process")
        if tuple(domain.get("scenario_ids", ())) != canonical_ids:
            raise ValueError("workload manifest domain scenario set/order drifted")

    return domains


def _fixture_state_digest(
    *,
    domain: Mapping[str, Any],
    scenario_id: str,
    target: str,
) -> str:
    return _canonical_digest(
        {
            "domain_id": domain["domain_id"],
            "workload_id": domain["workload_id"],
            "fixture_scheme": domain["fixture_scheme"],
            "ground_truth": domain["ground_truth"],
            "scenario_id": scenario_id,
            "target": target,
        }
    )


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
    """Execute one frozen, paired three-domain STUDY-012 replicate.

    Condition order is independently randomized within each workload/scenario
    pair. The pairing identity is invariant across I0-I6 and bound to the exact
    frozen workload manifest, fixture state, runtime/model identity and source
    commit.
    """
    if not isinstance(replicate_id, str) or not _REPLICATE_ID_RE.fullmatch(replicate_id):
        raise ValueError("replicate_id must be a non-empty path-opaque identifier")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if not isinstance(source_commit, str) or not _FULL_SHA_RE.fullmatch(source_commit):
        raise ValueError("source_commit must be a full lowercase 40-character Git SHA")

    manifest, workload_digest = _load_manifest(
        manifest_path=manifest_path,
        manifest=None,
    )
    domains = _validate_workload_manifest(manifest)
    scenario_by_id = {scenario.scenario_id: scenario for scenario in SCENARIOS}

    pairs: list[tuple[Mapping[str, Any], Any]] = []
    for domain in domains:
        for scenario_id in domain["scenario_ids"]:
            pairs.append((domain, scenario_by_id[scenario_id]))

    pair_rng = random.Random(_stable_random_seed("pair-order", seed, replicate_id))
    pair_rng.shuffle(pairs)

    records: list[dict[str, Any]] = []
    for domain, scenario in pairs:
        assert_safe_target(scenario.synthetic_target)
        fixture_digest = _fixture_state_digest(
            domain=domain,
            scenario_id=scenario.scenario_id,
            target=scenario.synthetic_target,
        )
        pair_id = (
            f"{domain['workload_id']}:{scenario.scenario_id}:{replicate_id}:{seed}"
        )
        condition_order = list(CONDITIONS)
        condition_rng = random.Random(
            _stable_random_seed(
                "condition-order",
                seed,
                replicate_id,
                domain["workload_id"],
                scenario.scenario_id,
            )
        )
        condition_rng.shuffle(condition_order)

        for condition_ordinal, condition in enumerate(condition_order):
            event = run_scenario(condition, scenario)
            records.append(
                {
                    "study_id": "STUDY-012",
                    "experiment_id": "ICT-EXP-0001",
                    "run_id": f"ICT-EXP-0001:{pair_id}:{condition}",
                    "pair_id": pair_id,
                    "condition": condition,
                    "condition_order_index": condition_ordinal,
                    "domain_id": domain["domain_id"],
                    "workload_id": domain["workload_id"],
                    "scenario_id": scenario.scenario_id,
                    "replicate_id": replicate_id,
                    "seed": seed,
                    "failure_class": scenario.failure_class,
                    "synthetic_target": scenario.synthetic_target,
                    "model_id": manifest["model_id"],
                    "runtime_version": manifest["runtime_version"],
                    "execution_engine": EXECUTION_ENGINE,
                    "execution_class": EXECUTION_CLASS,
                    "fallback_used": False,
                    "mission_contract_version": manifest["mission_contract_version"],
                    "fixture_state_sha256": fixture_digest,
                    "workload_manifest_sha256": workload_digest,
                    "manifest_sha256": workload_digest,
                    "source_commit": source_commit,
                    "attempted": event.attempted,
                    "blocked": event.blocked,
                    "violation_occurred": event.violation_occurred,
                    "transcript_claimed_success": event.transcript_claimed_success,
                    "evidence_detected_violation": event.evidence_detected_violation,
                }
            )

    return records
