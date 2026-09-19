"""JAR-EXP-0015 A/B/C original-contract live calibration composition."""

from dataclasses import asdict
from pathlib import Path
from typing import Any
import json

from .corpus import CalibrationCase
from .jar15_analysis import DecisionObservation, select_calibration_policy
from .jar15_cost_guard import build_jar15_cost_guard
from .jar15_durable_calibration import (
    jar15_calibration_checkpoint_path,
    run_jar15_abc_calibration,
)
from .jar15_preflight import evaluate_jar15_stage_preflight


class JAR15LiveError(RuntimeError):
    pass


def load_jar15_original_contracts(root: Path) -> dict[str, dict[str, Any]]:
    value = json.loads(
        (Path(root) / "data" / "jar_exp_0015_question_contracts_v01.json").read_text(
            encoding="utf-8"
        )
    )
    if value.get("schema_version") != "jar-exp-0015.question-contracts/0.1":
        raise JAR15LiveError("question contract schema mismatch")
    if value.get("status") != "FROZEN_PREEXECUTION":
        raise JAR15LiveError("question contracts are not frozen")
    if value.get("calibration_contract_mode") != "ORIGINAL_ONLY":
        raise JAR15LiveError("A/B/C calibration contract mode drift")
    contracts = value.get("original_contracts")
    if not isinstance(contracts, dict) or len(contracts) != 8:
        raise JAR15LiveError("original contracts missing")
    return contracts


def load_jar15_calibration_cases(root: Path) -> tuple[CalibrationCase, ...]:
    dataset = json.loads(
        (Path(root) / "data" / "jar_exp_0015_dataset_v03.json").read_text(
            encoding="utf-8"
        )
    )
    rows = [
        row for row in dataset.get("cases", []) if row.get("split") == "calibration"
    ]
    if len(rows) != 1952:
        raise JAR15LiveError("frozen calibration split cardinality mismatch")
    return tuple(
        CalibrationCase(
            case_id=row["case_id"],
            decision_type=row["decision_type"],
            state=row["state"],
            expected=row["expected"],
            critical=bool(row["critical"]),
        )
        for row in rows
    )


def run_authorized_jar15_abc_calibration(
    *,
    root: Path,
    client: Any,
    sdk: Any,
):
    root = Path(root)
    preflight = evaluate_jar15_stage_preflight(root, stage="calibration")
    if preflight.decision != "READY_TO_CALIBRATE":
        raise JAR15LiveError(
            "calibration authorization failed: " + ", ".join(preflight.blockers)
        )
    if preflight.requested_model != "jev-1.13.0":
        raise JAR15LiveError("unexpected model pin")
    if preflight.maximum_calls != 1952 or preflight.maximum_cost_usd != 5.38:
        raise JAR15LiveError("approved calibration ceiling drift")

    contracts = load_jar15_original_contracts(root)
    cases = load_jar15_calibration_cases(root)
    guard = build_jar15_cost_guard(root=root, stage="calibration")

    result = run_jar15_abc_calibration(
        client=client,
        sdk=sdk,
        requested_model=preflight.requested_model,
        contracts=contracts,
        cases=cases,
        cost_guard=guard,
        checkpoint_path=jar15_calibration_checkpoint_path(),
    )

    dataset = json.loads(
        (root / "data" / "jar_exp_0015_dataset_v03.json").read_text(encoding="utf-8")
    )
    protocol = json.loads(
        (root / "data" / "jar_exp_0015_protocol_v05.json").read_text(encoding="utf-8")
    )
    decision_observations = tuple(
        DecisionObservation(
            case_id=row.case_id,
            decision_type=row.decision_type,
            effective_confidence=row.effective_confidence,
            correct=row.correct,
            critical=row.critical,
        )
        for row in result.observations
    )
    policy = select_calibration_policy(
        decision_observations,
        dataset=dataset,
        protocol=protocol,
    )
    return result, policy
