import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from experiments.system_one_acceleration.cost_guard import (
    BudgetExceededError,
    BudgetLedger,
    BudgetReplayError,
    CostGuardError,
    PreRequestCostGuard,
    PricingDriftError,
    load_pricing_spec,
    verify_live_pricing,
)


ROOT = Path(__file__).resolve().parents[1]
PRICING = ROOT / "data" / "jar_exp_0014_typesafe_pricing_v01.json"


def _source_text():
    return (
        "Jev 1.13 jev-1.13.0 Price (per Btok / per Mtok) $42 / $0.042 "
        "Context length 64k tokens per request; 32k tokens for state plus the "
        "longest question. Output tokens are free."
    )


def _ledger(tmp_path, budget=10_000):
    spec = load_pricing_spec(PRICING)
    return spec, BudgetLedger(
        tmp_path / "budget.sqlite",
        run_id="test-run",
        approved_budget_microusd=budget,
        pricing_spec_sha256=spec.canonical_sha256,
    )


def test_conservative_request_and_full_calibration_bounds():
    spec = load_pricing_spec(PRICING)
    assert spec.model_id == "jev-1.13.0"
    assert spec.max_request_cost_microusd == 2753
    assert spec.max_request_cost_microusd * 158 == 434_974


def test_live_pricing_markers_accept_exact_frozen_assumptions():
    spec = load_pricing_spec(PRICING)
    verify_live_pricing(spec, lambda _url: _source_text())


def test_live_pricing_drift_fails_closed():
    spec = load_pricing_spec(PRICING)
    with pytest.raises(PricingDriftError, match="drifted"):
        verify_live_pricing(
            spec,
            lambda _url: _source_text().replace("$0.042", "$0.050"),
        )


def test_write_ahead_budget_denies_before_overrun(tmp_path):
    spec_budget = 2 * 2753
    spec, ledger = _ledger(tmp_path, budget=spec_budget)
    for index in range(2):
        ledger.reserve(
            request_id=f"r{index}",
            request_sha256=(f"{index + 1:x}" * 64)[:64],
            reserved_microusd=spec.max_request_cost_microusd,
        )
    assert ledger.used_microusd() == spec_budget
    with pytest.raises(BudgetExceededError):
        ledger.reserve(
            request_id="r2",
            request_sha256="f" * 64,
            reserved_microusd=spec.max_request_cost_microusd,
        )


def test_replay_is_denied_even_when_request_hash_matches(tmp_path):
    spec, ledger = _ledger(tmp_path)
    ledger.reserve(
        request_id="same",
        request_sha256="a" * 64,
        reserved_microusd=spec.max_request_cost_microusd,
    )
    with pytest.raises(BudgetReplayError):
        ledger.reserve(
            request_id="same",
            request_sha256="a" * 64,
            reserved_microusd=spec.max_request_cost_microusd,
        )


def test_crash_style_unfinished_reservation_survives_restart(tmp_path):
    spec, first = _ledger(tmp_path)
    first.reserve(
        request_id="crash",
        request_sha256="b" * 64,
        reserved_microusd=spec.max_request_cost_microusd,
    )
    second = BudgetLedger(
        tmp_path / "budget.sqlite",
        run_id="test-run",
        approved_budget_microusd=10_000,
        pricing_spec_sha256=spec.canonical_sha256,
    )
    assert second.used_microusd() == spec.max_request_cost_microusd
    with pytest.raises(BudgetReplayError):
        second.reserve(
            request_id="crash",
            request_sha256="b" * 64,
            reserved_microusd=spec.max_request_cost_microusd,
        )


def test_exact_semantic_request_is_bound_to_reservation(tmp_path):
    spec, ledger = _ledger(tmp_path)
    guard = PreRequestCostGuard(
        spec=spec, ledger=ledger, pricing_fetcher=lambda _url: _source_text()
    )
    reservation = guard.reserve_request(
        request_id="case-1",
        decision_type="continue_loop",
        state={
            "scenario": "work remains",
            "private_context": "must not cross boundary",
        },
        contract={"type": "noul", "instructions": "Continue?"},
        requested_model="jev-1.13.0",
    )
    assert reservation.projected_state == {"scenario": "work remains"}
    assert len(reservation.request_sha256) == 64
    assert ledger.used_microusd() == 2753


def test_malformed_usage_cannot_refund_or_exceed_reservation(tmp_path):
    spec, ledger = _ledger(tmp_path)
    guard = PreRequestCostGuard(
        spec=spec, ledger=ledger, pricing_fetcher=lambda _url: _source_text()
    )
    reservation = guard.reserve_request(
        request_id="case-2",
        decision_type="continue_loop",
        state={"scenario": "work remains"},
        contract={"type": "noul", "instructions": "Continue?"},
        requested_model="jev-1.13.0",
    )
    with pytest.raises(CostGuardError, match="exceeded frozen"):
        guard.complete_request(
            reservation,
            actual_input_tokens=spec.conservative_max_input_tokens_per_request + 1,
        )
    assert ledger.used_microusd() == reservation.reserved_microusd


def test_pricing_source_unavailable_denies_before_reservation(tmp_path):
    spec, ledger = _ledger(tmp_path)
    def fail(_url):
        raise OSError("offline")
    guard = PreRequestCostGuard(spec=spec, ledger=ledger, pricing_fetcher=fail)
    with pytest.raises(PricingDriftError, match="unavailable"):
        guard.reserve_request(
            request_id="no-network",
            decision_type="continue_loop",
            state={"scenario": "work remains"},
            contract={"type": "noul", "instructions": "Continue?"},
            requested_model="jev-1.13.0",
        )
    assert ledger.used_microusd() == 0


def test_concurrent_reservations_cannot_overrun_budget(tmp_path):
    spec = load_pricing_spec(PRICING)
    path = tmp_path / "race.sqlite"
    first = BudgetLedger(
        path,
        run_id="race-run",
        approved_budget_microusd=spec.max_request_cost_microusd,
        pricing_spec_sha256=spec.canonical_sha256,
    )
    second = BudgetLedger(
        path,
        run_id="race-run",
        approved_budget_microusd=spec.max_request_cost_microusd,
        pricing_spec_sha256=spec.canonical_sha256,
    )

    def attempt(ledger, request_id, digest):
        try:
            ledger.reserve(
                request_id=request_id,
                request_sha256=digest,
                reserved_microusd=spec.max_request_cost_microusd,
            )
            return "reserved"
        except BudgetExceededError:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                lambda args: attempt(*args),
                [
                    (first, "race-a", "c" * 64),
                    (second, "race-b", "d" * 64),
                ],
            )
        )
    assert sorted(outcomes) == ["blocked", "reserved"]
    assert first.used_microusd() == spec.max_request_cost_microusd


def test_stale_ledger_configuration_fails_closed(tmp_path):
    spec, _ledger_instance = _ledger(tmp_path)
    with pytest.raises(CostGuardError, match="configuration drift"):
        BudgetLedger(
            tmp_path / "budget.sqlite",
            run_id="test-run",
            approved_budget_microusd=20_000,
            pricing_spec_sha256=spec.canonical_sha256,
        )
    with pytest.raises(CostGuardError, match="configuration drift"):
        BudgetLedger(
            tmp_path / "budget.sqlite",
            run_id="test-run",
            approved_budget_microusd=10_000,
            pricing_spec_sha256="0" * 64,
        )
