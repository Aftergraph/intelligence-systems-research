#!/usr/bin/env python3
"""Deterministic semantic/falsification verifier for JAR-EXP-0014.

No provider SDK, credential, or network access is required. This sensor independently
recomputes critical bounds, exercises adversarial ledger/request paths, and verifies
the authority/call-order invariants required by the semantic review packet.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from types import SimpleNamespace
import inspect
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.calibration_preflight import evaluate_calibration_preflight
from experiments.system_one_acceleration.calibration_runner import CalibrationRunError, run_calibration
from experiments.system_one_acceleration.corpus import CalibrationCase
from experiments.system_one_acceleration.cost_guard import (
    BudgetExceededError,
    BudgetLedger,
    BudgetReplayError,
    CostGuardError,
    PreRequestCostGuard,
    PricingDriftError,
    calibration_budget_ledger_path,
    load_pricing_spec,
)
from experiments.system_one_acceleration.protocol import (
    DecisionPolicy,
    route_system_one_decision,
)


CHECKS: list[str] = []


def require(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        suffix = f": {detail}" if detail else ""
        raise SystemExit(f"FAIL[{name}]{suffix}")
    CHECKS.append(name)


def provider_fixture() -> str:
    return (
        "Jev 1.13 jev-1.13.0 Price (per Btok / per Mtok) $42 / $0.042 "
        "Context length 64k tokens per request; 32k tokens for state plus the "
        "longest question. Output tokens are free."
    )


class FakeQuestion:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeSDK:
    Noul = FakeQuestion
    Choice = FakeQuestion
    Score = FakeQuestion
    RetryPolicy = FakeQuestion


class WrongModelClient:
    def __init__(self):
        self.calls = 0

    def system_one(self, **kwargs):
        self.calls += 1
        key = next(iter(kwargs["questions"]))
        return SimpleNamespace(
            model="jev-wrong",
            answers={key: SimpleNamespace(type="noul", noul=0.99)},
            usage=SimpleNamespace(input_tokens=10, output_tokens=1),
        )


def make_guard(db: Path, *, run_id: str, budget: int, spec, fetcher=None):
    ledger = BudgetLedger(
        db,
        run_id=run_id,
        approved_budget_microusd=budget,
        pricing_spec_sha256=spec.canonical_sha256,
    )
    guard = PreRequestCostGuard(
        spec=spec,
        ledger=ledger,
        pricing_fetcher=fetcher or (lambda _url: provider_fixture()),
    )
    return ledger, guard


def main() -> None:
    raw = json.loads(
        (ROOT / "data" / "jar_exp_0014_typesafe_pricing_v01.json").read_text(
            encoding="utf-8"
        )
    )
    spec = load_pricing_spec(ROOT / "data" / "jar_exp_0014_typesafe_pricing_v01.json")

    # 1. Independent worst-case arithmetic.
    independent = int(
        (
            Decimal(int(raw["conservative_max_input_tokens_per_request"]))
            * Decimal(raw["input_usd_per_million_tokens"])
        ).to_integral_value(rounding=ROUND_CEILING)
    )
    require(
        "01_pricing_bound",
        raw["model_id"] == "jev-1.13.0"
        and Decimal(raw["input_usd_per_million_tokens"]) == Decimal("0.042")
        and Decimal(raw["output_usd_per_million_tokens"]) == Decimal("0")
        and int(raw["conservative_max_input_tokens_per_request"]) >= 65536
        and independent == 2753
        and independent * 158 == 434_974,
    )

    # 2. Authorized live entrypoint is pinned to canonical durable ledger + checkpoint.
    import experiments.system_one_acceleration.guarded_calibration as guarded
    import experiments.system_one_acceleration.durable_calibration as durable
    guarded_source = inspect.getsource(guarded.run_authorized_calibration)
    require(
        "02_canonical_ledger_entrypoint",
        "ledger_path=calibration_budget_ledger_path()" in guarded_source
        and "run_durable_calibration(" in guarded_source
        and "checkpoint_path=calibration_checkpoint_path()" in guarded_source
        and "ledger_path" not in inspect.signature(guarded.run_authorized_calibration).parameters
        and not calibration_budget_ledger_path().is_relative_to(ROOT)
        and not durable.calibration_checkpoint_path().is_relative_to(ROOT),
    )

    # 3. Reservation/claim/transport/completion ordering is explicit.
    import experiments.system_one_acceleration.calibration_runner as runner
    runner_source = inspect.getsource(runner.run_calibration)
    positions = [
        runner_source.index("reserve_request("),
        runner_source.index("begin_transport("),
        runner_source.index("invoke_system_one("),
        runner_source.index("complete_request("),
    ]
    require("03_transport_call_order", positions == sorted(positions) and len(set(positions)) == 4)

    # 4. SDK retries are explicitly disabled.
    import experiments.system_one_acceleration.client as client_module
    client_source = inspect.getsource(client_module.invoke_system_one)
    require("04_hidden_retries_disabled", "RetryPolicy(max_retries=0)" in client_source)

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        # 5. Insufficient budget denies before a reservation can exist.
        ledger, guard = make_guard(base / "deny.sqlite", run_id="deny", budget=independent - 1, spec=spec)
        try:
            guard.reserve_request(
                request_id="deny",
                decision_type="continue_loop",
                state={"scenario": "work remains"},
                contract={"type": "noul", "instructions": "Continue?"},
                requested_model=spec.model_id,
            )
        except BudgetExceededError:
            pass
        else:
            raise SystemExit("FAIL[05_pretransport_budget_denial]")
        require("05_pretransport_budget_denial", ledger.used_microusd() == 0)

        # 6. Concurrent distinct reservations cannot overrun the final slot.
        race_path = base / "race.sqlite"
        l1 = BudgetLedger(
            race_path,
            run_id="race",
            approved_budget_microusd=independent,
            pricing_spec_sha256=spec.canonical_sha256,
        )
        l2 = BudgetLedger(
            race_path,
            run_id="race",
            approved_budget_microusd=independent,
            pricing_spec_sha256=spec.canonical_sha256,
        )

        def reserve(ledger, rid, digest):
            try:
                ledger.reserve(
                    request_id=rid,
                    request_sha256=digest,
                    reserved_microusd=independent,
                )
                return "reserved"
            except BudgetExceededError:
                return "blocked"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = sorted(
                pool.map(
                    lambda args: reserve(*args),
                    [(l1, "a", "a" * 64), (l2, "b", "b" * 64)],
                )
            )
        require(
            "06_concurrent_budget_race",
            outcomes == ["blocked", "reserved"] and l1.used_microusd() == independent,
        )

        # 7. Pre-transport crash/resume does not double-reserve.
        resume_path = base / "resume.sqlite"
        r1 = BudgetLedger(
            resume_path,
            run_id="resume",
            approved_budget_microusd=independent,
            pricing_spec_sha256=spec.canonical_sha256,
        )
        r1.reserve(request_id="same", request_sha256="c" * 64, reserved_microusd=independent)
        r2 = BudgetLedger(
            resume_path,
            run_id="resume",
            approved_budget_microusd=independent,
            pricing_spec_sha256=spec.canonical_sha256,
        )
        r2.reserve(request_id="same", request_sha256="c" * 64, reserved_microusd=independent)
        require("07_pretransport_resume", r2.used_microusd() == independent)

        # 8. Only one worker can claim transport.
        def claim(ledger):
            try:
                ledger.begin_transport(request_id="same", request_sha256="c" * 64)
                return "claimed"
            except BudgetReplayError:
                return "blocked"

        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = sorted(pool.map(claim, (r1, r2)))
        require("08_atomic_transport_claim", claims == ["blocked", "claimed"])

        # 9. Claimed transport cannot be automatically replayed/resumed.
        try:
            r2.reserve(request_id="same", request_sha256="c" * 64, reserved_microusd=independent)
        except BudgetReplayError:
            pass
        else:
            raise SystemExit("FAIL[09_postclaim_replay_denied]")
        durable_source = inspect.getsource(durable.run_durable_calibration)
        require(
            "09_postclaim_replay_denied",
            "ambiguous prior transport without durable observation" in durable_source
            and "ledger has {record['status']} without durable observation" in durable_source,
        )

        # 10. Request-id substitution with a different semantic hash is denied.
        sub_path = base / "sub.sqlite"
        s1 = BudgetLedger(
            sub_path,
            run_id="sub",
            approved_budget_microusd=independent * 2,
            pricing_spec_sha256=spec.canonical_sha256,
        )
        s1.reserve(request_id="fixed", request_sha256="d" * 64, reserved_microusd=independent)
        try:
            s1.reserve(request_id="fixed", request_sha256="e" * 64, reserved_microusd=independent)
        except BudgetReplayError:
            pass
        else:
            raise SystemExit("FAIL[10_request_id_substitution]")
        require("10_request_id_substitution", True)

        # 11. Semantic state/contract mutations produce different bound request hashes.
        _, g1 = make_guard(base / "hash1.sqlite", run_id="h1", budget=independent, spec=spec)
        _, g2 = make_guard(base / "hash2.sqlite", run_id="h2", budget=independent, spec=spec)
        _, g3 = make_guard(base / "hash3.sqlite", run_id="h3", budget=independent, spec=spec)
        a = g1.reserve_request(
            request_id="a",
            decision_type="continue_loop",
            state={"scenario": "work remains"},
            contract={"type": "noul", "instructions": "Continue?"},
            requested_model=spec.model_id,
        )
        b = g2.reserve_request(
            request_id="b",
            decision_type="continue_loop",
            state={"scenario": "no work remains"},
            contract={"type": "noul", "instructions": "Continue?"},
            requested_model=spec.model_id,
        )
        c = g3.reserve_request(
            request_id="c",
            decision_type="continue_loop",
            state={"scenario": "work remains"},
            contract={"type": "noul", "instructions": "Stop?"},
            requested_model=spec.model_id,
        )
        require("11_semantic_request_binding", len({a.request_sha256, b.request_sha256, c.request_sha256}) == 3)

        # 12. Pricing drift before reservation consumes no budget.
        drift_ledger, drift_guard = make_guard(
            base / "drift.sqlite",
            run_id="drift",
            budget=independent,
            spec=spec,
            fetcher=lambda _url: provider_fixture().replace("$0.042", "$0.050"),
        )
        try:
            drift_guard.reserve_request(
                request_id="drift",
                decision_type="continue_loop",
                state={"scenario": "work remains"},
                contract={"type": "noul", "instructions": "Continue?"},
                requested_model=spec.model_id,
            )
        except PricingDriftError:
            pass
        else:
            raise SystemExit("FAIL[12_pricing_drift_before_reserve]")
        require("12_pricing_drift_before_reserve", drift_ledger.used_microusd() == 0)

        # 13. Pricing drift after reservation but before claim prevents transport claim.
        calls = {"n": 0}

        def drift_on_second(_url):
            calls["n"] += 1
            return provider_fixture() if calls["n"] == 1 else provider_fixture().replace("$0.042", "$0.050")

        claim_ledger, claim_guard = make_guard(
            base / "claimdrift.sqlite",
            run_id="claimdrift",
            budget=independent,
            spec=spec,
            fetcher=drift_on_second,
        )
        reservation = claim_guard.reserve_request(
            request_id="claimdrift",
            decision_type="continue_loop",
            state={"scenario": "work remains"},
            contract={"type": "noul", "instructions": "Continue?"},
            requested_model=spec.model_id,
        )
        try:
            claim_guard.begin_transport(reservation)
        except PricingDriftError:
            pass
        else:
            raise SystemExit("FAIL[13_pricing_drift_before_claim]")
        claim_ledger.reserve(
            request_id=reservation.request_id,
            request_sha256=reservation.request_sha256,
            reserved_microusd=reservation.reserved_microusd,
        )
        require("13_pricing_drift_before_claim", claim_ledger.used_microusd() == independent)

        # 14. Malformed/excess usage cannot release or exceed the frozen reservation.
        usage_ledger, usage_guard = make_guard(
            base / "usage.sqlite", run_id="usage", budget=independent, spec=spec
        )
        usage_res = usage_guard.reserve_request(
            request_id="usage",
            decision_type="continue_loop",
            state={"scenario": "work remains"},
            contract={"type": "noul", "instructions": "Continue?"},
            requested_model=spec.model_id,
        )
        usage_guard.begin_transport(usage_res)
        try:
            usage_guard.complete_request(
                usage_res,
                actual_input_tokens=spec.conservative_max_input_tokens_per_request + 1,
            )
        except CostGuardError:
            pass
        else:
            raise SystemExit("FAIL[14_malformed_usage_fail_closed]")
        require("14_malformed_usage_fail_closed", usage_ledger.used_microusd() == independent)

        # 15. A billed response from a different model is rejected.
        model_ledger, model_guard = make_guard(
            base / "model.sqlite", run_id="model", budget=independent, spec=spec
        )
        wrong_client = WrongModelClient()
        try:
            run_calibration(
                client=wrong_client,
                sdk=FakeSDK,
                requested_model=spec.model_id,
                contracts={"continue_loop": {"type": "noul", "instructions": "Continue?"}},
                cases=[
                    CalibrationCase(
                        "wrong-model",
                        "continue_loop",
                        {"scenario": "work remains"},
                        True,
                        False,
                    )
                ],
                maximum_calls=1,
                cost_guard=model_guard,
            )
        except CalibrationRunError:
            pass
        else:
            raise SystemExit("FAIL[15_returned_model_mismatch]")
        require("15_returned_model_mismatch", wrong_client.calls == 1)

    # 16. Authorization/review gates remain fail-closed across manifest drift.
    gate = json.loads((ROOT / "data" / "jar_exp_0014_calibration_gate_v01.json").read_text(encoding="utf-8"))
    approval = json.loads(
        (ROOT / gate["calibration_approval_ref"]).read_text(encoding="utf-8")
    )
    preflight = evaluate_calibration_preflight(ROOT)
    gate_pin = gate.get("calibration_manifest_sha256")
    approval_pin = approval.get("calibration_manifest_sha256")
    if gate.get("status") == "CALIBRATION_COMPLETE_NO_THRESHOLD":
        authorization_shape_ok = (
            gate.get("network_calls_authorized") is False
            and approval.get("approved") is True
            and approval.get("network_calls_authorized") is True
            and approval_pin == gate_pin
        )
    else:
        authorization_shape_ok = (
            gate.get("network_calls_authorized") is True
            and approval.get("approved") is True
            and approval.get("network_calls_authorized") is True
            and approval_pin == gate_pin
        )
    readiness_shape_ok = (
        (preflight.decision == "READY_TO_CALIBRATE" and not preflight.blockers)
        or (
            preflight.decision == "NO_GO"
            and "calibration_manifest_mismatch" in preflight.blockers
        )
        or (
            preflight.decision == "NO_GO"
            and set(preflight.blockers) == {"calibration_already_completed"}
        )
    )
    require(
        "16_authorization_and_review_gate",
        authorization_shape_ok and readiness_shape_ok,
    )

    # 17. Ineligible/authority-sensitive decisions never turn into execution authority.
    ineligible = route_system_one_decision(
        decision_type="approve_payment",
        answer_kind="noul",
        answer_value=0.99,
        reported_confidence=None,
        transport_ok=True,
        schema_ok=True,
        authority_sensitive_ambiguity=False,
        evidence_conflict=False,
        policy=DecisionPolicy(0.5),
    )
    ambiguous = route_system_one_decision(
        decision_type="needs_human",
        answer_kind="noul",
        answer_value=0.99,
        reported_confidence=None,
        transport_ok=True,
        schema_ok=True,
        authority_sensitive_ambiguity=True,
        evidence_conflict=False,
        policy=DecisionPolicy(0.5),
    )
    require(
        "17_authority_boundary",
        ineligible.decision == "fallback"
        and ambiguous.decision == "escalate"
        and ineligible.authority_bypassed is False
        and ambiguous.authority_bypassed is False,
    )

    # 18. Known pricing TOCTOU is explicitly bounded as an external-provider limitation:
    # validation happens both at reserve and immediately before atomic claim; there is no
    # local retry after claim. Instantaneous provider-side billing semantic drift after the
    # second check cannot be eliminated by a client-only mechanism and is not represented as zero risk.
    import experiments.system_one_acceleration.cost_guard as cg
    reserve_source = inspect.getsource(cg.PreRequestCostGuard.reserve_request)
    claim_source = inspect.getsource(cg.PreRequestCostGuard.begin_transport)
    require(
        "18_pricing_toctou_mitigated_not_erased",
        "verify_live_pricing" in reserve_source
        and "verify_live_pricing" in claim_source
        and "begin_transport" in claim_source,
    )

    require("count", len([name for name in CHECKS if name != "count"]) == 18)
    print("PASS: JAR-EXP-0014 deterministic semantic verifier")
    print("falsification_attempts=18")
    print("verdict=PASS_WITH_FINDINGS")
    print("finding=pricing validation cannot make provider-side post-check billing drift impossible")
    for name in CHECKS:
        if name != "count":
            print(f"check={name}:PASS")


if __name__ == "__main__":
    main()
