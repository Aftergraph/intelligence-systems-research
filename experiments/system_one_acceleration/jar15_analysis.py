"""JAR-EXP-0015 prospective policy selection and hold-out isolation.

This module is zero-network. It enforces that threshold/policy selection consumes
only the frozen calibration split, while hold-out evaluation is impossible until
a calibration-derived policy has been frozen.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence

from experiments.system_one_acceleration.calibration import (
    CalibrationDecision,
    ThresholdResult,
    evaluate_threshold,
    select_threshold,
)


class JAR15AnalysisError(RuntimeError):
    pass


@dataclass(frozen=True)
class DecisionObservation:
    case_id: str
    decision_type: str
    effective_confidence: float
    correct: bool
    critical: bool


def canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _dataset_index(dataset: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    cases = dataset.get("cases")
    if not isinstance(cases, list):
        raise JAR15AnalysisError("dataset cases missing")
    index: dict[str, Mapping[str, Any]] = {}
    for row in cases:
        if not isinstance(row, Mapping):
            raise JAR15AnalysisError("dataset case invalid")
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise JAR15AnalysisError("dataset case id invalid")
        if case_id in index:
            raise JAR15AnalysisError("dataset case ids not unique")
        index[case_id] = row
    return index


def inference_inputs(dataset: Mapping[str, Any], *, split: str) -> tuple[dict[str, Any], ...]:
    if split not in {"calibration", "holdout"}:
        raise ValueError("split must be calibration or holdout")
    rows = []
    for row in _dataset_index(dataset).values():
        if row.get("split") != split:
            continue
        rows.append(
            {
                "case_id": row["case_id"],
                "decision_type": row["decision_type"],
                "state": json.loads(json.dumps(row["state"], sort_keys=True)),
            }
        )
    return tuple(rows)


def _bind_observations(
    observations: Sequence[DecisionObservation],
    *,
    dataset: Mapping[str, Any],
    required_split: str,
) -> tuple[DecisionObservation, ...]:
    index = _dataset_index(dataset)
    expected_ids = {
        case_id
        for case_id, row in index.items()
        if row.get("split") == required_split
    }
    seen: set[str] = set()
    bound: list[DecisionObservation] = []

    for obs in observations:
        if obs.case_id in seen:
            raise JAR15AnalysisError(f"duplicate observation: {obs.case_id}")
        seen.add(obs.case_id)
        row = index.get(obs.case_id)
        if row is None:
            raise JAR15AnalysisError(f"observation outside frozen dataset: {obs.case_id}")
        if row.get("split") != required_split:
            raise JAR15AnalysisError(
                f"{required_split} analysis received {row.get('split')} case: {obs.case_id}"
            )
        if row.get("decision_type") != obs.decision_type:
            raise JAR15AnalysisError(f"decision type mismatch: {obs.case_id}")
        if bool(row.get("critical")) != obs.critical:
            raise JAR15AnalysisError(f"critical binding mismatch: {obs.case_id}")
        if not 0.0 <= float(obs.effective_confidence) <= 1.0:
            raise JAR15AnalysisError(f"confidence outside [0,1]: {obs.case_id}")
        bound.append(obs)

    if seen != expected_ids:
        missing = len(expected_ids - seen)
        extra = len(seen - expected_ids)
        raise JAR15AnalysisError(
            f"{required_split} observations do not exactly cover frozen split "
            f"(missing={missing}, extra={extra})"
        )
    return tuple(sorted(bound, key=lambda row: row.case_id))


def observations_sha256(observations: Iterable[DecisionObservation]) -> str:
    rows = [
        {
            "case_id": row.case_id,
            "decision_type": row.decision_type,
            "effective_confidence": row.effective_confidence,
            "correct": row.correct,
            "critical": row.critical,
        }
        for row in sorted(observations, key=lambda item: item.case_id)
    ]
    return canonical_sha256(rows)


def _threshold_dict(result: ThresholdResult) -> dict[str, Any]:
    return asdict(result)


def select_calibration_policy(
    observations: Sequence[DecisionObservation],
    *,
    dataset: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    bound = _bind_observations(
        observations,
        dataset=dataset,
        required_split="calibration",
    )
    rules = protocol["threshold_rule"]
    minimum_coverage = float(rules["minimum_accepted_coverage"])
    maximum_wilson_error = float(rules["maximum_wilson_upper_error"])

    global_result = select_threshold(
        (
            CalibrationDecision(
                effective_confidence=row.effective_confidence,
                correct=row.correct,
                critical=row.critical,
            )
            for row in bound
        ),
        minimum_coverage=minimum_coverage,
        maximum_wilson_error=maximum_wilson_error,
    )

    per_type: dict[str, dict[str, Any]] = {}
    for decision_type in protocol["dataset"]["decision_types"]:
        type_rows = [row for row in bound if row.decision_type == decision_type]
        result = select_threshold(
            (
                CalibrationDecision(
                    effective_confidence=row.effective_confidence,
                    correct=row.correct,
                    critical=row.critical,
                )
                for row in type_rows
            ),
            minimum_coverage=minimum_coverage,
            maximum_wilson_error=maximum_wilson_error,
        )
        per_type[decision_type] = _threshold_dict(result)

    feasible_types = sorted(
        decision_type
        for decision_type, result in per_type.items()
        if result["feasible"]
    )
    fallback_types = sorted(set(per_type) - set(feasible_types))

    policy = {
        "schema_version": "jar-exp-0015.policy/0.1",
        "experiment_id": "JAR-EXP-0015",
        "status": "FROZEN_PREHOLDOUT",
        "protocol_version": protocol["schema_version"],
        "dataset_sha256": protocol["dataset"]["dataset_sha256"],
        "split_manifest_sha256": protocol["dataset"]["split_manifest_sha256"],
        "calibration_observations_sha256": observations_sha256(bound),
        "calibration_observation_count": len(bound),
        "global_threshold": _threshold_dict(global_result),
        "per_decision_type": per_type,
        "selective_cascade": {
            "eligible_decision_types": feasible_types,
            "fallback_decision_types": fallback_types,
        },
        "holdout_consumed": False,
    }
    policy["policy_sha256"] = canonical_sha256(policy)
    return policy


def verify_frozen_policy(policy: Mapping[str, Any], protocol: Mapping[str, Any]) -> None:
    if policy.get("schema_version") != "jar-exp-0015.policy/0.1":
        raise JAR15AnalysisError("policy schema invalid")
    if policy.get("status") != "FROZEN_PREHOLDOUT":
        raise JAR15AnalysisError("policy is not frozen before holdout")
    if policy.get("holdout_consumed") is not False:
        raise JAR15AnalysisError("policy already indicates holdout consumption")
    if policy.get("protocol_version") != protocol.get("schema_version"):
        raise JAR15AnalysisError("policy protocol version drift")
    if policy.get("dataset_sha256") != protocol["dataset"]["dataset_sha256"]:
        raise JAR15AnalysisError("policy dataset binding mismatch")
    if policy.get("split_manifest_sha256") != protocol["dataset"]["split_manifest_sha256"]:
        raise JAR15AnalysisError("policy split binding mismatch")
    candidate = dict(policy)
    claimed = candidate.pop("policy_sha256", None)
    if claimed != canonical_sha256(candidate):
        raise JAR15AnalysisError("policy content hash mismatch")


def evaluate_holdout_policy(
    policy: Mapping[str, Any],
    observations: Sequence[DecisionObservation],
    *,
    dataset: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    verify_frozen_policy(policy, protocol)
    bound = _bind_observations(
        observations,
        dataset=dataset,
        required_split="holdout",
    )

    per_type_results: dict[str, dict[str, Any]] = {}
    promotion = protocol["promotion"]
    for decision_type in protocol["dataset"]["decision_types"]:
        rows = [row for row in bound if row.decision_type == decision_type]
        selected = policy["per_decision_type"][decision_type]
        threshold = selected.get("threshold")
        if not selected.get("feasible") or threshold is None:
            per_type_results[decision_type] = {
                "promoted": False,
                "reason": "CALIBRATION_NO_THRESHOLD",
                "accepted": 0,
                "coverage": 0.0,
                "critical_errors": 0,
                "wilson_upper": None,
            }
            continue

        result = evaluate_threshold(
            (
                CalibrationDecision(
                    effective_confidence=row.effective_confidence,
                    correct=row.correct,
                    critical=row.critical,
                )
                for row in rows
            ),
            float(threshold),
            minimum_coverage=float(protocol["threshold_rule"]["minimum_accepted_coverage"]),
            maximum_wilson_error=float(promotion["per_class_holdout_wilson_upper_max"]),
        )
        promoted = (
            result.feasible
            and result.critical_errors <= int(promotion["critical_holdout_errors_max"])
        )
        value = _threshold_dict(result)
        value["promoted"] = promoted
        value["reason"] = "PASS" if promoted else "HOLDOUT_CRITERIA_FAILED"
        per_type_results[decision_type] = value

    eligible = [
        name for name, result in per_type_results.items() if result["promoted"]
    ]
    total_accepted = sum(result["accepted"] for result in per_type_results.values())
    aggregate_coverage = total_accepted / len(bound)
    outcome = (
        "PROMOTION_ELIGIBLE"
        if eligible
        and aggregate_coverage >= float(promotion["aggregate_holdout_coverage_min"])
        else promotion["failure_outcome"]
    )
    return {
        "schema_version": "jar-exp-0015.holdout-evaluation/0.1",
        "experiment_id": "JAR-EXP-0015",
        "policy_sha256": policy["policy_sha256"],
        "holdout_observations_sha256": observations_sha256(bound),
        "holdout_observation_count": len(bound),
        "per_decision_type": per_type_results,
        "promoted_decision_types": sorted(eligible),
        "aggregate_accepted_coverage": aggregate_coverage,
        "outcome": outcome,
    }
