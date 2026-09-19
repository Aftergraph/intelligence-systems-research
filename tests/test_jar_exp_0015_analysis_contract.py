import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from experiments.system_one_acceleration.jar15_analysis import (
    DecisionObservation,
    JAR15AnalysisError,
    evaluate_holdout_policy,
    inference_inputs,
    select_calibration_policy,
    verify_frozen_policy,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET = json.loads((ROOT / "data" / "jar_exp_0015_dataset_v02.json").read_text(encoding="utf-8"))
PROTOCOL = json.loads((ROOT / "data" / "jar_exp_0015_protocol_v03.json").read_text(encoding="utf-8"))
POLICY_SCHEMA = json.loads((ROOT / "schemas" / "jar-exp-0015-policy.v0.1.json").read_text(encoding="utf-8"))
ANALYSIS_GATE = json.loads((ROOT / "data" / "jar_exp_0015_analysis_gate_v01.json").read_text(encoding="utf-8"))


def observations(split: str, *, correct: bool = True, confidence: float = 0.99):
    return [
        DecisionObservation(
            case_id=row["case_id"],
            decision_type=row["decision_type"],
            effective_confidence=confidence,
            correct=correct,
            critical=bool(row["critical"]),
        )
        for row in DATASET["cases"]
        if row["split"] == split
    ]


def test_inference_inputs_do_not_expose_labels_or_split():
    rows = inference_inputs(DATASET, split="holdout")
    assert len(rows) == 1952
    assert all(set(row) == {"case_id", "decision_type", "state"} for row in rows)
    assert all("expected" not in row for row in rows)
    assert all("split" not in row for row in rows)


def test_policy_selection_requires_exact_calibration_split():
    calibration = observations("calibration")
    with pytest.raises(JAR15AnalysisError, match="exactly cover frozen split"):
        select_calibration_policy(
            calibration[:-1],
            dataset=DATASET,
            protocol=PROTOCOL,
        )


def test_policy_selection_rejects_single_holdout_leak():
    calibration = observations("calibration")
    holdout = observations("holdout")
    contaminated = calibration[:-1] + [holdout[0]]
    with pytest.raises(JAR15AnalysisError, match="calibration analysis received holdout case"):
        select_calibration_policy(
            contaminated,
            dataset=DATASET,
            protocol=PROTOCOL,
        )


def test_all_correct_calibration_can_freeze_content_addressed_policy():
    policy = select_calibration_policy(
        observations("calibration"),
        dataset=DATASET,
        protocol=PROTOCOL,
    )
    assert policy["status"] == "FROZEN_PREHOLDOUT"
    assert policy["calibration_observation_count"] == 1952
    assert policy["holdout_consumed"] is False
    assert policy["global_threshold"]["feasible"] is True
    assert len(policy["per_decision_type"]) == 8
    assert all(result["feasible"] for result in policy["per_decision_type"].values())
    assert policy["selective_cascade"]["fallback_decision_types"] == []
    verify_frozen_policy(policy, PROTOCOL)
    Draft202012Validator(POLICY_SCHEMA).validate(policy)


def test_policy_hash_tamper_is_rejected():
    policy = select_calibration_policy(
        observations("calibration"),
        dataset=DATASET,
        protocol=PROTOCOL,
    )
    policy["per_decision_type"]["risk_level"]["threshold"] = 0.123
    with pytest.raises(JAR15AnalysisError, match="policy content hash mismatch"):
        verify_frozen_policy(policy, PROTOCOL)


def test_holdout_evaluation_rejects_calibration_ids():
    policy = select_calibration_policy(
        observations("calibration"),
        dataset=DATASET,
        protocol=PROTOCOL,
    )
    mixed = observations("holdout")
    mixed[-1] = observations("calibration")[0]
    with pytest.raises(JAR15AnalysisError, match="holdout analysis received calibration case"):
        evaluate_holdout_policy(
            policy,
            mixed,
            dataset=DATASET,
            protocol=PROTOCOL,
        )


def test_all_correct_holdout_promotes_all_feasible_types():
    policy = select_calibration_policy(
        observations("calibration"),
        dataset=DATASET,
        protocol=PROTOCOL,
    )
    result = evaluate_holdout_policy(
        policy,
        observations("holdout"),
        dataset=DATASET,
        protocol=PROTOCOL,
    )
    assert result["holdout_observation_count"] == 1952
    assert result["aggregate_accepted_coverage"] == 1.0
    assert result["outcome"] == "PROMOTION_ELIGIBLE"
    assert result["promoted_decision_types"] == sorted(PROTOCOL["dataset"]["decision_types"])


def test_analysis_gate_is_fail_closed_before_calibration():
    assert ANALYSIS_GATE["status"] == "CALIBRATION_NOT_RUN"
    assert ANALYSIS_GATE["calibration_policy_ref"] is None
    assert ANALYSIS_GATE["calibration_policy_sha256"] is None
    assert ANALYSIS_GATE["holdout_evaluation_authorized"] is False
    assert ANALYSIS_GATE["holdout_consumed"] is False
    assert ANALYSIS_GATE["network_calls_authorized"] is False
