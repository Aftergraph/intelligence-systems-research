from pathlib import Path

from experiments.system_one_acceleration.jar15_cost_guard import (
    build_jar15_cost_guard,
    jar15_budget_ledger_path,
    load_jar15_pricing_spec,
)
from experiments.system_one_acceleration.jar15_preflight import (
    evaluate_jar15_stage_preflight,
)

ROOT = Path(__file__).resolve().parents[1]


def pricing_fixture() -> str:
    return (
        "Jev 1.13 jev-1.13.0 Price (per Btok / per Mtok) $42 / $0.042 "
        "Context length 64k tokens per request. Output tokens are free."
    )


def test_jar15_pricing_math_and_model_pin():
    spec = load_jar15_pricing_spec(
        ROOT / "data" / "jar_exp_0015_typesafe_pricing_v01.json"
    )
    assert spec.model_id == "jev-1.13.0"
    assert spec.max_request_cost_microusd == 2753
    assert 1952 * spec.max_request_cost_microusd == 5_373_856
    assert 3904 * spec.max_request_cost_microusd == 10_747_712


def test_stage_ledgers_are_canonical_and_separate():
    calibration = jar15_budget_ledger_path("calibration")
    holdout = jar15_budget_ledger_path("holdout")
    assert calibration != holdout
    assert "jar-exp-0015" in str(calibration)
    assert calibration.name == "calibration-budget-v01.sqlite"
    assert holdout.name == "holdout-budget-v01.sqlite"


def test_cost_guard_reserves_with_stage_budget(tmp_path):
    guard = build_jar15_cost_guard(
        root=ROOT,
        stage="calibration",
        ledger_path=tmp_path / "cal.sqlite",
        pricing_fetcher=lambda _url: pricing_fixture(),
    )
    reservation = guard.reserve_request(
        request_id="J15-test-reservation",
        decision_type="continue_loop",
        state={"scenario": "Two acceptance criteria remain unverified."},
        contract={"type": "noul", "instructions": "Should work continue?"},
        requested_model="jev-1.13.0",
    )
    assert reservation.reserved_microusd == 2753
    assert guard.ledger.used_microusd() == 2753


def test_calibration_preflight_is_fail_closed_on_protected_gates():
    result = evaluate_jar15_stage_preflight(ROOT, stage="calibration")
    assert result.decision == "NO_GO"
    assert set(result.blockers) == {
        "calibration_semantic_review_not_recorded",
        "calibration_owner_approval_not_recorded",
        "calibration_network_calls_not_authorized",
    }
    assert result.requested_model == "jev-1.13.0"
    assert result.maximum_calls == 1952
    assert result.maximum_cost_usd == 5.38


def test_holdout_preflight_is_independently_fail_closed():
    result = evaluate_jar15_stage_preflight(ROOT, stage="holdout")
    assert result.decision == "NO_GO"
    assert set(result.blockers) == {
        "holdout_frozen_policy_not_recorded",
        "holdout_semantic_review_not_recorded",
        "holdout_owner_approval_not_recorded",
        "holdout_evaluation_not_authorized",
        "holdout_network_calls_not_authorized",
    }
    assert result.requested_model == "jev-1.13.0"
    assert result.maximum_calls == 1952
    assert result.maximum_cost_usd == 5.38
