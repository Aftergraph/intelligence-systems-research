#!/usr/bin/env python3
"""Independent zero-network JAR-EXP-0015 cost/preflight verifier."""

import json
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.cost_guard import CostGuardError
from experiments.system_one_acceleration.jar15_cost_guard import (
    build_jar15_cost_guard,
    jar15_budget_ledger_path,
    load_jar15_pricing_spec,
)
from experiments.system_one_acceleration.jar15_preflight import (
    evaluate_jar15_stage_preflight,
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


def require(name, condition):
    if not condition:
        raise SystemExit(f"FAIL[{name}]")
    print(f"check={name}:PASS")


def pricing_fixture():
    return (
        "Jev 1.13 jev-1.13.0 Price (per Btok / per Mtok) $42 / $0.042 "
        "Context length 64k tokens per request. Output tokens are free."
    )


def first_case(split):
    return next(row for row in DATASET["cases"] if row["split"] == split)


def main():
    spec = load_jar15_pricing_spec(
        ROOT / "data" / "jar_exp_0015_typesafe_pricing_v01.json"
    )
    require("01_model_pin", spec.model_id == "jev-1.13.0")
    require("02_per_request_cost", spec.max_request_cost_microusd == 2753)
    require("03_calibration_worst_case", 1952 * spec.max_request_cost_microusd == 5_373_856)
    require("04_full_two_stage_worst_case", 3904 * spec.max_request_cost_microusd == 10_747_712)
    require("05_calibration_gate_call_ceiling", CAL_GATE["max_provider_calls"] == 1952)
    require("06_holdout_gate_call_ceiling", HOLD_GATE["max_provider_calls"] == 1952)
    require("07_calibration_gate_budget", CAL_GATE["max_cost_usd"] == 5.38)
    require("08_holdout_gate_budget", HOLD_GATE["max_cost_usd"] == 5.38)
    require("09_zero_sdk_retries", CAL_GATE["sdk_retries_allowed"] is False and HOLD_GATE["sdk_retries_allowed"] is False)
    require(
        "10_stage_network_scope",
        HOLD_GATE["network_calls_authorized"] is False
        and (
            CAL_GATE["network_calls_authorized"] is False
            or CAL_GATE["network_calls_authorized"] is True
        ),
    )

    cal_pre = evaluate_jar15_stage_preflight(ROOT, stage="calibration")
    if (
        CAL_GATE.get("semantic_review_ref") is not None
        and CAL_GATE.get("owner_approval_ref") is not None
        and CAL_GATE.get("network_calls_authorized") is True
    ):
        require("11_calibration_ready", cal_pre.decision == "READY_TO_CALIBRATE")
        require("12_calibration_blockers_exact", not cal_pre.blockers)
    else:
        require("11_calibration_ready", cal_pre.decision == "NO_GO")
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
            "12_calibration_blockers_exact",
            set(cal_pre.blockers) == expected_calibration_blockers,
        )
    hold_pre = evaluate_jar15_stage_preflight(ROOT, stage="holdout")
    require("13_holdout_no_go", hold_pre.decision == "NO_GO")
    require(
        "14_holdout_blockers_exact",
        set(hold_pre.blockers) == {
            "holdout_frozen_policy_not_recorded",
            "holdout_semantic_review_not_recorded",
            "holdout_owner_approval_not_recorded",
            "holdout_evaluation_not_authorized",
            "holdout_network_calls_not_authorized",
        },
    )

    require("15_ledger_paths_distinct", jar15_budget_ledger_path("calibration") != jar15_budget_ledger_path("holdout"))

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cal = build_jar15_cost_guard(
            root=ROOT,
            stage="calibration",
            ledger_path=td / "cal.sqlite",
            pricing_fetcher=lambda _url: pricing_fixture(),
        )
        hold = build_jar15_cost_guard(
            root=ROOT,
            stage="holdout",
            ledger_path=td / "hold.sqlite",
            pricing_fetcher=lambda _url: pricing_fixture(),
        )
        require("16_calibration_allowed_ids", len(cal.allowed_case_ids) == 1952)
        require("17_holdout_allowed_ids", len(hold.allowed_case_ids) == 1952)
        require("18_stage_id_sets_disjoint", cal.allowed_case_ids.isdisjoint(hold.allowed_case_ids))

        wrong = first_case("holdout")
        fetched = False
        def should_not_fetch(_url):
            nonlocal fetched
            fetched = True
            raise AssertionError("network/pricing fetch should not occur")
        blocked = False
        guarded = build_jar15_cost_guard(
            root=ROOT,
            stage="calibration",
            ledger_path=td / "cal2.sqlite",
            pricing_fetcher=should_not_fetch,
        )
        try:
            guarded.reserve_request(
                request_id=wrong["case_id"],
                decision_type=wrong["decision_type"],
                state=wrong["state"],
                contract={"type": "noul", "instructions": "Synthetic verifier"},
                requested_model="jev-1.13.0",
            )
        except CostGuardError:
            blocked = True
        require("19_wrong_split_blocked", blocked)
        require("20_wrong_split_zero_network", fetched is False)

    print("PASS: JAR-EXP-0015 stage cost/preflight verifier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
