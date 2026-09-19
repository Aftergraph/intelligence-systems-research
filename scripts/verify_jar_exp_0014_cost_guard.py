#!/usr/bin/env python3
"""Independent no-network verifier for the JAR-EXP-0014 TypeSafe cost guard."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.calibration_preflight import evaluate_calibration_preflight
from experiments.system_one_acceleration.cost_guard import (
    BudgetExceededError,
    BudgetLedger,
    BudgetReplayError,
    PreRequestCostGuard,
    PricingDriftError,
    calibration_budget_ledger_path,
    load_pricing_spec,
)


SPEC_PATH = ROOT / "data" / "jar_exp_0014_typesafe_pricing_v01.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("FAIL: " + message)


def provider_fixture() -> str:
    return (
        "Jev 1.13 jev-1.13.0 Price (per Btok / per Mtok) $42 / $0.042 "
        "Context length 64k tokens per request; 32k tokens for state plus the "
        "longest question. Output tokens are free."
    )


def main() -> None:
    raw = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    price = Decimal(raw["input_usd_per_million_tokens"])
    max_tokens = int(raw["conservative_max_input_tokens_per_request"])
    independent_per_request = int(
        (Decimal(max_tokens) * price).to_integral_value(rounding=ROUND_CEILING)
    )
    require(independent_per_request == 2753, "independent per-request bound")
    require(independent_per_request * 158 == 434_974, "158-case bound")

    spec = load_pricing_spec(SPEC_PATH)
    require(spec.max_request_cost_microusd == independent_per_request, "module bound")
    require(spec.model_id == "jev-1.13.0", "concrete model pin")

    canonical = calibration_budget_ledger_path()
    require(not canonical.is_relative_to(ROOT), "durable ledger must live outside repo")

    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "budget.sqlite"
        budget = 2 * independent_per_request
        first = BudgetLedger(
            path,
            run_id="blackbox",
            approved_budget_microusd=budget,
            pricing_spec_sha256=spec.canonical_sha256,
        )
        second = BudgetLedger(
            path,
            run_id="blackbox",
            approved_budget_microusd=budget,
            pricing_spec_sha256=spec.canonical_sha256,
        )

        def reserve(ledger, request_id, digest):
            try:
                ledger.reserve(
                    request_id=request_id,
                    request_sha256=digest,
                    reserved_microusd=independent_per_request,
                )
                return "reserved"
            except BudgetExceededError:
                return "blocked"

        first.reserve(
            request_id="fixed",
            request_sha256="a" * 64,
            reserved_microusd=independent_per_request,
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = sorted(
                pool.map(
                    lambda args: reserve(*args),
                    [
                        (first, "race-a", "b" * 64),
                        (second, "race-b", "c" * 64),
                    ],
                )
            )
        require(outcomes == ["blocked", "reserved"], "race must admit exactly one")
        require(first.used_microusd() == budget, "ledger must stop at approved budget")

        reopened = BudgetLedger(
            path,
            run_id="blackbox",
            approved_budget_microusd=budget,
            pricing_spec_sha256=spec.canonical_sha256,
        )
        require(reopened.used_microusd() == budget, "restart must preserve reservations")
        # A crash before transport may resume the same semantic reservation
        # without consuming budget again.
        reopened.reserve(
            request_id="fixed",
            request_sha256="a" * 64,
            reserved_microusd=independent_per_request,
        )
        require(reopened.used_microusd() == budget, "resume must not double-spend")
        reopened.begin_transport(request_id="fixed", request_sha256="a" * 64)
        try:
            reopened.begin_transport(request_id="fixed", request_sha256="a" * 64)
        except BudgetReplayError:
            pass
        else:
            raise SystemExit("FAIL: second transport claim was not denied")

    with tempfile.TemporaryDirectory() as temp:
        ledger = BudgetLedger(
            Path(temp) / "binding.sqlite",
            run_id="binding",
            approved_budget_microusd=independent_per_request,
            pricing_spec_sha256=spec.canonical_sha256,
        )
        guard = PreRequestCostGuard(
            spec=spec,
            ledger=ledger,
            pricing_fetcher=lambda _url: provider_fixture(),
        )
        reservation = guard.reserve_request(
            request_id="semantic",
            decision_type="continue_loop",
            state={"scenario": "work remains", "secret_noise": "drop me"},
            contract={"type": "noul", "instructions": "Continue?"},
            requested_model="jev-1.13.0",
        )
        require(reservation.projected_state == {"scenario": "work remains"}, "projection")
        require(len(reservation.request_sha256) == 64, "request binding hash")
        guard.begin_transport(reservation)

    with tempfile.TemporaryDirectory() as temp:
        ledger = BudgetLedger(
            Path(temp) / "drift.sqlite",
            run_id="drift",
            approved_budget_microusd=independent_per_request,
            pricing_spec_sha256=spec.canonical_sha256,
        )
        guard = PreRequestCostGuard(
            spec=spec,
            ledger=ledger,
            pricing_fetcher=lambda _url: provider_fixture().replace("$0.042", "$0.050"),
        )
        try:
            guard.reserve_request(
                request_id="drift",
                decision_type="continue_loop",
                state={"scenario": "work remains"},
                contract={"type": "noul", "instructions": "Continue?"},
                requested_model="jev-1.13.0",
            )
        except PricingDriftError:
            pass
        else:
            raise SystemExit("FAIL: pricing drift was not denied")
        require(ledger.used_microusd() == 0, "drift denial must precede reservation")

    preflight = evaluate_calibration_preflight(ROOT)
    require(preflight.decision == "NO_GO", "calibration must remain protected")
    require(
        set(preflight.blockers)
        == {"calibration_semantic_review_not_recorded"},
        "unexpected calibration blocker set",
    )
    require(preflight.maximum_calls == 158, "call ceiling")
    require(preflight.maximum_cost_usd == 0.44, "USD ceiling")
    require(preflight.requested_model == "jev-1.13.0", "preflight model")

    print("PASS: JAR-EXP-0014 cost guard independent verifier")
    print("per_request_microusd=2753")
    print("calibration_worst_case_microusd=434974")
    print("protected_blockers=semantic_review")


if __name__ == "__main__":
    main()
