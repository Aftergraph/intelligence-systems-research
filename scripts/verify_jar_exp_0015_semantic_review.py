#!/usr/bin/env python3
"""Deterministic no-network semantic falsification verifier for JAR-EXP-0015."""

from collections import Counter, defaultdict
from pathlib import Path
import inspect
import json
import math
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.calibration import wilson_upper
from experiments.system_one_acceleration.integrity import (
    jar15_calibration_manifest_sha256,
)
from experiments.system_one_acceleration.jar15_analysis import (
    DecisionObservation,
    JAR15AnalysisError,
    inference_inputs,
    select_calibration_policy,
    verify_frozen_policy,
)
from experiments.system_one_acceleration.jar15_cost_guard import (
    build_jar15_cost_guard,
    jar15_budget_ledger_path,
    load_jar15_pricing_spec,
)
from experiments.system_one_acceleration.jar15_preflight import (
    evaluate_jar15_stage_preflight,
)
from experiments.system_one_acceleration.state_projection import (
    project_decision_state,
)

ACTIVE = json.loads(
    (ROOT / "data" / "jar_exp_0015_active_protocol.json").read_text(encoding="utf-8")
)
PROTOCOL = json.loads(
    (ROOT / "data" / "jar_exp_0015_protocol_v05.json").read_text(encoding="utf-8")
)
DATASET = json.loads(
    (ROOT / "data" / "jar_exp_0015_dataset_v03.json").read_text(encoding="utf-8")
)
CAL_GATE = json.loads(
    (ROOT / "data" / "jar_exp_0015_calibration_gate_v01.json").read_text(encoding="utf-8")
)
HOLD_GATE = json.loads(
    (ROOT / "data" / "jar_exp_0015_holdout_gate_v01.json").read_text(encoding="utf-8")
)
ARM_D_GATE = json.loads(
    (ROOT / "data" / "jar_exp_0015_arm_d_gate_v01.json").read_text(encoding="utf-8")
)


def require(name: str, condition: bool) -> None:
    if not condition:
        raise SystemExit(f"FAIL[{name}]")
    print(f"check={name}:PASS")


def _obs(split: str):
    return [
        DecisionObservation(
            case_id=row["case_id"],
            decision_type=row["decision_type"],
            effective_confidence=0.99,
            correct=True,
            critical=bool(row["critical"]),
        )
        for row in DATASET["cases"]
        if row["split"] == split
    ]


def main() -> int:
    rows = DATASET["cases"]
    manifest = jar15_calibration_manifest_sha256(ROOT)

    require("01_manifest_computable", len(manifest) == 64)
    require(
        "02_active_protocol_v05",
        ACTIVE["active_protocol_ref"] == "data/jar_exp_0015_protocol_v05.json"
        and PROTOCOL["schema_version"] == "jar-exp-0015.protocol/0.5",
    )
    require(
        "03_dataset_v03_bound",
        PROTOCOL["dataset"]["dataset_ref"] == "data/jar_exp_0015_dataset_v03.json"
        and DATASET["schema_version"] == "jar-exp-0015.dataset/0.3",
    )
    require("04_dataset_cardinality", len(rows) == 3904)
    require(
        "05_split_cardinality",
        Counter(row["split"] for row in rows)
        == {"calibration": 1952, "holdout": 1952},
    )

    by_type = defaultdict(Counter)
    for row in rows:
        by_type[row["decision_type"]][row["split"]] += 1
    require(
        "06_per_type_split",
        len(by_type) == 8
        and all(v == {"calibration": 244, "holdout": 244} for v in by_type.values()),
    )

    require(
        "07_sample_size_falsifies_v01",
        wilson_upper(0, 24) > 0.05 and wilson_upper(0, 16) > 0.05,
    )
    require(
        "08_sample_size_v05_feasible_at_floor",
        math.ceil(244 * 0.30) == 74
        and wilson_upper(0, 74) <= 0.05
        and PROTOCOL["sample_size_feasibility"]["floor_accepted_n_at_30_percent"] == 74,
    )

    projection_ok = True
    route_labels_hidden = True
    for row in rows:
        projected = project_decision_state(
            decision_type=row["decision_type"], state=row["state"]
        )
        if projected != row["state"] or set(projected) != {"scenario"}:
            projection_ok = False
            break
        if row["decision_type"] in {"route_model", "route_tool_family"}:
            if str(row["expected"]).lower() in projected["scenario"].lower():
                route_labels_hidden = False
                break
    require("09_projection_semantics_survive", projection_ok)
    require("10_route_labels_not_verbatim", route_labels_hidden)

    holdout_inputs = inference_inputs(DATASET, split="holdout")
    require(
        "11_inference_inputs_hide_labels",
        len(holdout_inputs) == 1952
        and all(set(row) == {"case_id", "decision_type", "state"} for row in holdout_inputs),
    )

    cal = _obs("calibration")
    hold = _obs("holdout")
    leaked = cal[:-1] + [hold[0]]
    leak_blocked = False
    try:
        select_calibration_policy(leaked, dataset=DATASET, protocol=PROTOCOL)
    except JAR15AnalysisError:
        leak_blocked = True
    require("12_holdout_leak_blocked", leak_blocked)

    missing_blocked = False
    try:
        select_calibration_policy(cal[:-1], dataset=DATASET, protocol=PROTOCOL)
    except JAR15AnalysisError:
        missing_blocked = True
    require("13_incomplete_calibration_blocked", missing_blocked)

    policy = select_calibration_policy(cal, dataset=DATASET, protocol=PROTOCOL)
    verify_frozen_policy(policy, PROTOCOL)
    require(
        "14_policy_content_addressed",
        policy["status"] == "FROZEN_PREHOLDOUT"
        and policy["holdout_consumed"] is False
        and len(policy["policy_sha256"]) == 64,
    )

    pricing = load_jar15_pricing_spec(
        ROOT / "data" / "jar_exp_0015_typesafe_pricing_v01.json"
    )
    require(
        "15_pricing_model_pin",
        pricing.model_id == "jev-1.13.0"
        and pricing.max_request_cost_microusd == 2753,
    )
    require(
        "16_calibration_budget_math",
        1952 * pricing.max_request_cost_microusd == 5_373_856
        and CAL_GATE["max_cost_usd"] == 5.38,
    )
    require(
        "17_holdout_budget_math",
        1952 * pricing.max_request_cost_microusd == 5_373_856
        and HOLD_GATE["max_cost_usd"] == 5.38,
    )
    require(
        "18_sdk_retries_disabled",
        CAL_GATE["sdk_retries_allowed"] is False
        and HOLD_GATE["sdk_retries_allowed"] is False,
    )

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cal_guard = build_jar15_cost_guard(
            root=ROOT,
            stage="calibration",
            ledger_path=td / "cal.sqlite",
            pricing_fetcher=lambda _url: (
                "Jev 1.13 jev-1.13.0 Price (per Btok / per Mtok) $42 / $0.042 "
                "Context length 64k tokens per request. Output tokens are free."
            ),
        )
        hold_guard = build_jar15_cost_guard(
            root=ROOT,
            stage="holdout",
            ledger_path=td / "hold.sqlite",
            pricing_fetcher=lambda _url: (
                "Jev 1.13 jev-1.13.0 Price (per Btok / per Mtok) $42 / $0.042 "
                "Context length 64k tokens per request. Output tokens are free."
            ),
        )
        require(
            "19_stage_case_sets_exact_and_disjoint",
            len(cal_guard.allowed_case_ids) == 1952
            and len(hold_guard.allowed_case_ids) == 1952
            and cal_guard.allowed_case_ids.isdisjoint(hold_guard.allowed_case_ids),
        )

    require(
        "20_stage_ledgers_distinct",
        jar15_budget_ledger_path("calibration")
        != jar15_budget_ledger_path("holdout"),
    )

    cal_pre = evaluate_jar15_stage_preflight(ROOT, stage="calibration")
    if (
        CAL_GATE.get("semantic_review_ref") is not None
        and CAL_GATE.get("owner_approval_ref") is not None
        and CAL_GATE.get("network_calls_authorized") is True
    ):
        require(
            "21_calibration_protected_fail_closed",
            cal_pre.decision == "READY_TO_CALIBRATE"
            and not cal_pre.blockers,
        )
    else:
        expected_calibration_blockers = set()
        if CAL_GATE.get("semantic_review_ref") is None:
            expected_calibration_blockers.add(
                "calibration_semantic_review_not_recorded"
            )
        if CAL_GATE.get("owner_approval_ref") is None:
            expected_calibration_blockers.add(
                "calibration_owner_approval_not_recorded"
            )
        if CAL_GATE.get("network_calls_authorized") is not True:
            expected_calibration_blockers.add(
                "calibration_network_calls_not_authorized"
            )
        require(
            "21_calibration_protected_fail_closed",
            cal_pre.decision == "NO_GO"
            and set(cal_pre.blockers) == expected_calibration_blockers,
        )
    hold_pre = evaluate_jar15_stage_preflight(ROOT, stage="holdout")
    require(
        "22_holdout_independently_fail_closed",
        hold_pre.decision == "NO_GO"
        and "holdout_frozen_policy_not_recorded" in hold_pre.blockers
        and "holdout_network_calls_not_authorized" in hold_pre.blockers,
    )

    require(
        "23_authority_boundary_advisory_only",
        PROTOCOL["authority_boundary"]
        == {
            "system_one_role": "ADVISORY_ONLY",
            "grants_authority": False,
            "grants_verification": False,
            "grants_execution_truth": False,
        },
    )
    require(
        "24_arm_d_separately_protected",
        ARM_D_GATE["status"] == "NOT_AUTHORIZED"
        and ARM_D_GATE["network_calls_authorized"] is False
        and ARM_D_GATE["max_provider_calls"] == 732
        and ARM_D_GATE["max_cost_usd"] == 2.02,
    )
    require(
        "25_mutable_gates_not_in_manifest",
        all(
            item not in inspect.getsource(sys.modules[
                "experiments.system_one_acceleration.integrity"
            ])
            for item in (
                '"data/jar_exp_0015_analysis_gate_v01.json"',
                '"data/jar_exp_0015_calibration_gate_v01.json"',
                '"data/jar_exp_0015_holdout_gate_v01.json"',
            )
        ),
    )

    print("verdict=PASS_WITH_FINDINGS")
    print("falsification_attempts=25")
    print(f"calibration_manifest_sha256={manifest}")
    print(
        "finding=Provider-side pricing/billing semantics may still drift after "
        "the final client-side pricing validation and before provider billing."
    )
    print(
        "disposition=Accepted external-provider limitation; double validation, "
        "stage hard caps, frozen IDs, zero SDK retries, and no automatic replay remain mandatory."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
