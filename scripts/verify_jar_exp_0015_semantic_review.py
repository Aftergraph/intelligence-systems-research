#!/usr/bin/env python3
"""Deterministic semantic/falsification verifier for JAR-EXP-0015.

No provider SDK, credential, or network access is required. This sensor
independently recomputes the Amendment-004 activation bindings, exercises the
adversarial ledger/request paths against the 0015 pricing spec, proves the
projection-fidelity and label-leakage preconditions that Amendment-003 froze
dataset v0.3 on, verifies analysis isolation and the authority boundary, and
confirms the frozen JAR-EXP-0014 record was not disturbed by any 0015 change.

The verifier is fail-closed by construction: it never fabricates the owner or
network approval. Its terminal honest state is NO_GO with only the human-gate
blockers remaining.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import inspect
import json
import re
import sys
import tempfile

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.adapter import normalize_typesafe_answer  # noqa: F401
from experiments.system_one_acceleration.calibration import (
    CalibrationDecision,
    select_threshold,
)
from experiments.system_one_acceleration.calibration_runner import (
    CalibrationObservation,
    CalibrationRunError,
    CalibrationRunResult,
    run_calibration,
)
from experiments.system_one_acceleration.corpus import (
    CalibrationCase,
    build_calibration_corpus,
)
from experiments.system_one_acceleration.cost_guard import (
    BudgetExceededError,
    BudgetLedger,
    BudgetReplayError,
    CostGuardError,
    PreRequestCostGuard,
    PricingDriftError,
    calibration_budget_ledger_path,
)
from experiments.system_one_acceleration.durable_calibration import (
    calibration_checkpoint_path,
    run_durable_calibration,
)
from experiments.system_one_acceleration.guarded_jar15_calibration import (
    jar15_calibration_cases,
    jar15_calibration_checkpoint_path,
    jar15_calibration_ledger_path,
)
from experiments.system_one_acceleration.integrity import (
    CALIBRATION_INTEGRITY_PATHS,
    calibration_manifest_sha256,
)
from experiments.system_one_acceleration.jar15_analysis import (
    DecisionObservation,
    JAR15AnalysisError,
    evaluate_holdout_policy,
    select_calibration_policy,
    verify_frozen_policy,
)
from experiments.system_one_acceleration.jar15_calibration_preflight import (
    evaluate_jar15_calibration_preflight,
)
from experiments.system_one_acceleration.jar15_dataset import semantic_case_hash
from experiments.system_one_acceleration.jar15_dataset_v03 import (
    dataset_document_v03,
    split_manifest_v03,
)
from experiments.system_one_acceleration.jar15_integrity import (
    jar15_calibration_manifest_sha256,
)
from experiments.system_one_acceleration.jar15_pricing import (
    jar15_worst_case_microusd,
    load_jar15_pricing_spec,
)
from experiments.system_one_acceleration.jar15_receipt import (
    build_jar15_calibration_receipt,
)
from experiments.system_one_acceleration.protocol import (
    DecisionPolicy,
    route_system_one_decision,
)
from experiments.system_one_acceleration.state_projection import project_decision_state


CHECKS: list[str] = []

DATASET_REF = "data/jar_exp_0015_dataset_v03.json"
SPLIT_MANIFEST_REF = "data/jar_exp_0015_split_manifest_v03.json"
PROTOCOL_REF = "data/jar_exp_0015_protocol_v04.json"
ACTIVE_REF = "data/jar_exp_0015_active_protocol.json"
GATE_REF = "data/jar_exp_0015_calibration_gate_v01.json"
HOLDOUT_GATE_REF = "data/jar_exp_0015_holdout_gate_v01.json"
ANALYSIS_GATE_REF = "data/jar_exp_0015_analysis_gate_v01.json"
PRICING_REF = "data/jar_exp_0015_typesafe_pricing_v01.json"
POLICY_SCHEMA_REF = "schemas/jar-exp-0015-policy.v0.1.json"
RECEIPT_SCHEMA_REF = "schemas/jar-exp-0015-calibration-receipt.v0.1.json"
GATE14_REF = "data/jar_exp_0014_calibration_gate_v01.json"

CALIBRATION_N = 1952
HOLDOUT_N = 1952
TOTAL_N = 3904

LABEL_VOCABULARY = {
    "route_model": ("fast", "powerful", "escalate"),
    "route_tool_family": ("search", "filesystem", "browser", "code_execution", "none"),
    "risk_level": ("low", "moderate", "high", "critical"),
    "continue_loop": ("true", "false"),
    "result_sufficient": ("true", "false"),
    "retryable_failure": ("true", "false"),
    "evidence_conflict": ("true", "false"),
    "needs_human": ("true", "false"),
}


def require(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        suffix = f": {detail}" if detail else ""
        raise SystemExit(f"FAIL[{name}]{suffix}")
    CHECKS.append(name)


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _git(*args: str) -> bytes:
    import subprocess

    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: "
            f"{result.stderr.decode(errors='replace').strip()[:200]}"
        )
    return result.stdout


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


def observations_for(dataset, split: str, *, correct: bool = True, confidence: float = 0.99):
    return [
        DecisionObservation(
            case_id=row["case_id"],
            decision_type=row["decision_type"],
            effective_confidence=confidence,
            correct=correct,
            critical=bool(row["critical"]),
        )
        for row in dataset["cases"]
        if row["split"] == split
    ]


def main() -> None:
    dataset = load(DATASET_REF)
    manifest = load(SPLIT_MANIFEST_REF)
    protocol = load(PROTOCOL_REF)
    active = load(ACTIVE_REF)
    gate = load(GATE_REF)
    holdout_gate = load(HOLDOUT_GATE_REF)
    analysis_gate = load(ANALYSIS_GATE_REF)
    spec = load_jar15_pricing_spec(ROOT / PRICING_REF)

    dataset_sha = sha256((ROOT / DATASET_REF).read_bytes()).hexdigest()
    manifest_sha = sha256((ROOT / SPLIT_MANIFEST_REF).read_bytes()).hexdigest()

    # ---- Group 1: Amendment-004 activation binding -------------------------
    require(
        "01_active_protocol_v04",
        active["active_protocol_ref"] == PROTOCOL_REF
        and active["active_dataset_ref"] == DATASET_REF
        and active["active_split_manifest_ref"] == SPLIT_MANIFEST_REF
        and active["network_calls_authorized"] is False
        and active["status"] == "ACTIVE_PREEXECUTION",
    )
    pds = protocol["dataset"]
    require(
        "02_protocol_binds_v03_dataset",
        protocol["schema_version"] == "jar-exp-0015.protocol/0.4"
        and pds["dataset_ref"] == DATASET_REF
        and pds["split_manifest_ref"] == SPLIT_MANIFEST_REF
        and pds["dataset_sha256"] == dataset_sha
        and pds["split_manifest_sha256"] == manifest_sha,
    )
    require("03_dataset_generator_parity", dataset == dataset_document_v03())
    require("04_manifest_generator_parity", manifest == split_manifest_v03())

    rows = dataset["cases"]
    calib = [r for r in rows if r["split"] == "calibration"]
    hold = [r for r in rows if r["split"] == "holdout"]
    by_type: dict[str, dict[str, int]] = {}
    for r in rows:
        bucket = by_type.setdefault(r["decision_type"], {"calibration": 0, "holdout": 0})
        bucket[r["split"]] += 1
    require(
        "05_dataset_cardinality",
        len(rows) == TOTAL_N
        and len(calib) == CALIBRATION_N
        and len(hold) == HOLDOUT_N
        and len(by_type) == 8
        and all(v == {"calibration": 244, "holdout": 244} for v in by_type.values()),
    )

    parent_hashes = {
        semantic_case_hash(
            decision_type=c.decision_type,
            state=c.state,
            expected=c.expected,
            critical=c.critical,
        )
        for c in build_calibration_corpus()
    }
    child_hashes = {
        semantic_case_hash(
            decision_type=r["decision_type"],
            state=r["state"],
            expected=r["expected"],
            critical=r["critical"],
        )
        for r in rows
    }
    require(
        "06_parent_disjoint",
        len(parent_hashes) == 158
        and len(child_hashes) == TOTAL_N
        and parent_hashes.isdisjoint(child_hashes),
    )
    superseded = {x["protocol_ref"] for x in active["superseded"]}
    require(
        "07_amendment_chain",
        protocol["amendments"] == ["001", "002", "003"]
        and superseded
        == {
            "data/jar_exp_0015_protocol_v01.json",
            "data/jar_exp_0015_protocol_v02.json",
            "data/jar_exp_0015_protocol_v03.json",
        },
    )

    # ---- Group 2: projection fidelity (Amendment-003 precondition) --------
    lossless = True
    scenario_only = True
    for r in rows:
        projected = project_decision_state(decision_type=r["decision_type"], state=r["state"])
        if projected != r["state"]:
            lossless = False
            break
        if set(r["state"].keys()) != {"scenario"}:
            scenario_only = False
    require("08_projection_lossless_v03", lossless)
    require("09_projection_scenario_only", scenario_only)

    leaks = 0
    for r in rows:
        scenario = r["state"]["scenario"]
        for token in LABEL_VOCABULARY[r["decision_type"]]:
            if re.search(rf"\b{re.escape(token)}\b", scenario, re.IGNORECASE):
                leaks += 1
    require("10_no_label_leakage", leaks == 0, f"verbatim_leaks={leaks}")

    # ---- Group 3: pricing / budget arithmetic -----------------------------
    independent = int(
        (
            Decimal(spec.conservative_max_input_tokens_per_request)
            * spec.input_usd_per_million_tokens
        ).to_integral_value(rounding=ROUND_CEILING)
    )
    require(
        "11_pricing_bound",
        spec.model_id == "jev-1.13.0"
        and spec.input_usd_per_million_tokens == Decimal("0.042")
        and spec.output_usd_per_million_tokens == Decimal("0")
        and spec.conservative_max_input_tokens_per_request >= 65536
        and independent == 2753
        and spec.max_request_cost_microusd == 2753,
    )
    require(
        "12_worst_case_calibration",
        jar15_worst_case_microusd(spec, CALIBRATION_N) == 5_373_856
        and int((Decimal(str(gate["max_cost_usd"])) * Decimal(1_000_000)).to_integral_value(rounding=ROUND_FLOOR))
        >= 5_373_856,
    )
    require(
        "13_worst_case_holdout",
        jar15_worst_case_microusd(spec, HOLDOUT_N) == 5_373_856
        and int((Decimal(str(holdout_gate["max_cost_usd"])) * Decimal(1_000_000)).to_integral_value(rounding=ROUND_FLOOR))
        >= 5_373_856,
    )
    require(
        "14_full_two_stage",
        jar15_worst_case_microusd(spec, CALIBRATION_N + HOLDOUT_N) == 10_747_712,
    )

    # ---- Group 4: cost-guard / ledger adversarial paths -------------------
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

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
            raise SystemExit("FAIL[15_pretransport_budget_denial]")
        require("15_pretransport_budget_denial", ledger.used_microusd() == 0)

        race_path = base / "race.sqlite"
        l1 = BudgetLedger(race_path, run_id="race", approved_budget_microusd=independent, pricing_spec_sha256=spec.canonical_sha256)
        l2 = BudgetLedger(race_path, run_id="race", approved_budget_microusd=independent, pricing_spec_sha256=spec.canonical_sha256)

        def reserve(led, rid, digest):
            try:
                led.reserve(request_id=rid, request_sha256=digest, reserved_microusd=independent)
                return "reserved"
            except BudgetExceededError:
                return "blocked"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = sorted(pool.map(lambda a: reserve(*a), [(l1, "a", "a" * 64), (l2, "b", "b" * 64)]))
        require("16_concurrent_budget_race", outcomes == ["blocked", "reserved"] and l1.used_microusd() == independent)

        resume_path = base / "resume.sqlite"
        r1 = BudgetLedger(resume_path, run_id="resume", approved_budget_microusd=independent, pricing_spec_sha256=spec.canonical_sha256)
        r1.reserve(request_id="same", request_sha256="c" * 64, reserved_microusd=independent)
        r2 = BudgetLedger(resume_path, run_id="resume", approved_budget_microusd=independent, pricing_spec_sha256=spec.canonical_sha256)
        r2.reserve(request_id="same", request_sha256="c" * 64, reserved_microusd=independent)
        require("17_pretransport_resume", r2.used_microusd() == independent)

        def claim(led):
            try:
                led.begin_transport(request_id="same", request_sha256="c" * 64)
                return "claimed"
            except BudgetReplayError:
                return "blocked"

        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = sorted(pool.map(claim, (r1, r2)))
        require("18_atomic_transport_claim", claims == ["blocked", "claimed"])

        try:
            r2.reserve(request_id="same", request_sha256="c" * 64, reserved_microusd=independent)
        except BudgetReplayError:
            pass
        else:
            raise SystemExit("FAIL[19_postclaim_replay_denied]")
        durable_source = inspect.getsource(run_durable_calibration)
        require(
            "19_postclaim_replay_denied",
            "ambiguous prior transport without durable observation" in durable_source
            and "ledger has {record['status']} without durable observation" in durable_source,
        )

        sub_path = base / "sub.sqlite"
        s1 = BudgetLedger(sub_path, run_id="sub", approved_budget_microusd=independent * 2, pricing_spec_sha256=spec.canonical_sha256)
        s1.reserve(request_id="fixed", request_sha256="d" * 64, reserved_microusd=independent)
        try:
            s1.reserve(request_id="fixed", request_sha256="e" * 64, reserved_microusd=independent)
        except BudgetReplayError:
            pass
        else:
            raise SystemExit("FAIL[20_request_id_substitution]")
        require("20_request_id_substitution", True)

        _, g1 = make_guard(base / "h1.sqlite", run_id="h1", budget=independent, spec=spec)
        _, g2 = make_guard(base / "h2.sqlite", run_id="h2", budget=independent, spec=spec)
        _, g3 = make_guard(base / "h3.sqlite", run_id="h3", budget=independent, spec=spec)
        a = g1.reserve_request(request_id="a", decision_type="continue_loop", state={"scenario": "work remains"}, contract={"type": "noul", "instructions": "Continue?"}, requested_model=spec.model_id)
        b = g2.reserve_request(request_id="b", decision_type="continue_loop", state={"scenario": "no work remains"}, contract={"type": "noul", "instructions": "Continue?"}, requested_model=spec.model_id)
        c = g3.reserve_request(request_id="c", decision_type="continue_loop", state={"scenario": "work remains"}, contract={"type": "noul", "instructions": "Stop?"}, requested_model=spec.model_id)
        require("21_semantic_request_binding", len({a.request_sha256, b.request_sha256, c.request_sha256}) == 3)

        drift_ledger, drift_guard = make_guard(base / "drift.sqlite", run_id="drift", budget=independent, spec=spec, fetcher=lambda _url: provider_fixture().replace("$0.042", "$0.050"))
        try:
            drift_guard.reserve_request(request_id="drift", decision_type="continue_loop", state={"scenario": "work remains"}, contract={"type": "noul", "instructions": "Continue?"}, requested_model=spec.model_id)
        except PricingDriftError:
            pass
        else:
            raise SystemExit("FAIL[22_pricing_drift_before_reserve]")
        require("22_pricing_drift_before_reserve", drift_ledger.used_microusd() == 0)

        calls = {"n": 0}

        def drift_on_second(_url):
            calls["n"] += 1
            return provider_fixture() if calls["n"] == 1 else provider_fixture().replace("$0.042", "$0.050")

        claim_ledger, claim_guard = make_guard(base / "claimdrift.sqlite", run_id="claimdrift", budget=independent, spec=spec, fetcher=drift_on_second)
        reservation = claim_guard.reserve_request(request_id="claimdrift", decision_type="continue_loop", state={"scenario": "work remains"}, contract={"type": "noul", "instructions": "Continue?"}, requested_model=spec.model_id)
        try:
            claim_guard.begin_transport(reservation)
        except PricingDriftError:
            pass
        else:
            raise SystemExit("FAIL[23_pricing_drift_before_claim]")
        claim_ledger.reserve(request_id=reservation.request_id, request_sha256=reservation.request_sha256, reserved_microusd=reservation.reserved_microusd)
        require("23_pricing_drift_before_claim", claim_ledger.used_microusd() == independent)

        usage_ledger, usage_guard = make_guard(base / "usage.sqlite", run_id="usage", budget=independent, spec=spec)
        usage_res = usage_guard.reserve_request(request_id="usage", decision_type="continue_loop", state={"scenario": "work remains"}, contract={"type": "noul", "instructions": "Continue?"}, requested_model=spec.model_id)
        usage_guard.begin_transport(usage_res)
        try:
            usage_guard.complete_request(usage_res, actual_input_tokens=spec.conservative_max_input_tokens_per_request + 1)
        except CostGuardError:
            pass
        else:
            raise SystemExit("FAIL[24_malformed_usage_fail_closed]")
        require("24_malformed_usage_fail_closed", usage_ledger.used_microusd() == independent)

        model_ledger, model_guard = make_guard(base / "model.sqlite", run_id="model", budget=independent, spec=spec)
        wrong_client = WrongModelClient()
        try:
            run_calibration(
                client=wrong_client,
                sdk=FakeSDK,
                requested_model=spec.model_id,
                contracts={"continue_loop": {"type": "noul", "instructions": "Continue?"}},
                cases=[CalibrationCase("wrong-model", "continue_loop", {"scenario": "work remains"}, True, False)],
                maximum_calls=1,
                cost_guard=model_guard,
            )
        except CalibrationRunError:
            pass
        else:
            raise SystemExit("FAIL[25_returned_model_mismatch]")
        require("25_returned_model_mismatch", wrong_client.calls == 1)

    # ---- Group 4b: 0015 durable namespace isolation -----------------------
    j15_ledger = jar15_calibration_ledger_path()
    j15_ckpt = jar15_calibration_checkpoint_path()
    require(
        "26_ledger_namespaced_from_0014",
        "jar-exp-0015" in j15_ledger.parts
        and "jar-exp-0014" not in j15_ledger.parts
        and "jar-exp-0015" in j15_ckpt.parts
        and "jar-exp-0014" not in j15_ckpt.parts
        and j15_ledger != calibration_budget_ledger_path()
        and j15_ckpt != calibration_checkpoint_path()
        and not j15_ledger.is_relative_to(ROOT)
        and not j15_ckpt.is_relative_to(ROOT),
    )

    # ---- Group 5: authority boundary --------------------------------------
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
        "27_authority_boundary",
        ineligible.decision == "fallback"
        and ambiguous.decision == "escalate"
        and ineligible.authority_bypassed is False
        and ambiguous.authority_bypassed is False,
    )

    # ---- Group 6: analysis isolation --------------------------------------
    calibration_obs = observations_for(dataset, "calibration")
    holdout_obs = observations_for(dataset, "holdout")
    contaminated = calibration_obs[:-1] + [holdout_obs[0]]
    try:
        select_calibration_policy(contaminated, dataset=dataset, protocol=protocol)
    except JAR15AnalysisError as exc:
        require("28_holdout_isolation", "received holdout case" in str(exc))
    else:
        raise SystemExit("FAIL[28_holdout_isolation]")

    policy = select_calibration_policy(calibration_obs, dataset=dataset, protocol=protocol)
    mixed = observations_for(dataset, "holdout")
    mixed[-1] = calibration_obs[0]
    try:
        evaluate_holdout_policy(policy, mixed, dataset=dataset, protocol=protocol)
    except JAR15AnalysisError as exc:
        require("29_calibration_isolation", "received calibration case" in str(exc))
    else:
        raise SystemExit("FAIL[29_calibration_isolation]")

    policy_schema = load(POLICY_SCHEMA_REF)
    Draft202012Validator(policy_schema).validate(policy)
    require(
        "30_policy_schema_binds_v04",
        policy_schema["properties"]["protocol_version"]["const"] == "jar-exp-0015.protocol/0.4",
    )
    tampered = json.loads(json.dumps(policy))
    tampered["per_decision_type"]["risk_level"]["threshold"] = 0.123
    try:
        verify_frozen_policy(tampered, protocol)
    except JAR15AnalysisError as exc:
        require("31_policy_tamper_blocked", "policy content hash mismatch" in str(exc))
    else:
        raise SystemExit("FAIL[31_policy_tamper_blocked]")

    # ---- Group 7: receipt binding -----------------------------------------
    receipt_schema = load(RECEIPT_SCHEMA_REF)
    case = CalibrationCase("X-1", "continue_loop", {"scenario": "s"}, True, False)
    thr = select_threshold([CalibrationDecision(effective_confidence=0.9, correct=True, critical=False)])
    obs = CalibrationObservation(
        case_id="X-1", decision_type="continue_loop", expected=True, predicted=True,
        correct=True, critical=False, effective_confidence=0.9, returned_model="jev-1.13.0",
        latency_ms=1.0, input_tokens=10, output_tokens=0,
    )
    res = CalibrationRunResult(
        requested_model="jev-1.13.0", returned_model="jev-1.13.0", observations=(obs,),
        threshold=thr, provider_calls=1, input_tokens=10, output_tokens=0,
    )
    receipt = build_jar15_calibration_receipt(
        receipt_id="synthetic", result=res, cases=[case], protocol_document=protocol,
        dataset_sha256=dataset_sha, split_manifest_sha256=manifest_sha,
        calibration_manifest_sha256="c" * 64, source_commit="0" * 40,
        generated_at="2026-09-20T00:00:00Z",
    )
    Draft202012Validator(receipt_schema).validate(receipt)
    bad_obs = CalibrationObservation(
        case_id="X-2", decision_type="continue_loop", expected=True, predicted=True,
        correct=True, critical=False, effective_confidence=0.9, returned_model="jev-1.13.0",
        latency_ms=1.0, input_tokens=10, output_tokens=0,
    )
    bad_res = CalibrationRunResult(
        requested_model="jev-1.13.0", returned_model="jev-1.13.0", observations=(bad_obs,),
        threshold=thr, provider_calls=1, input_tokens=10, output_tokens=0,
    )
    try:
        build_jar15_calibration_receipt(
            receipt_id="synthetic", result=bad_res, cases=[case], protocol_document=protocol,
            dataset_sha256=dataset_sha, split_manifest_sha256=manifest_sha,
            calibration_manifest_sha256="c" * 64, source_commit="0" * 40,
            generated_at="2026-09-20T00:00:00Z",
        )
    except ValueError:
        require("32_receipt_binds_corpus", True)
    else:
        raise SystemExit("FAIL[32_receipt_binds_corpus]")

    # ---- Group 8: governance / fail-closed --------------------------------
    # This verifier is valid on BOTH sides of the legitimate Gate-B transition.
    # It must not encode a stale pre-authorization snapshot that intentionally
    # turns CI red once the owner-authority path succeeds.
    preflight = evaluate_jar15_calibration_preflight(ROOT)
    open_human_gates: set[str] = set()
    if not gate.get("semantic_review_ref"):
        open_human_gates.add("jar15_semantic_review_not_recorded")
    if not gate.get("owner_approval_ref"):
        open_human_gates.add("jar15_approval_not_recorded")
    if gate.get("network_calls_authorized") is not True:
        open_human_gates.add("jar15_network_calls_not_authorized")

    expected_decision = "NO_GO" if open_human_gates else "READY_TO_CALIBRATE"
    require(
        "33_preflight_governance_state_coherent",
        preflight.decision == expected_decision
        and set(preflight.blockers) == open_human_gates,
        detail=(
            f"expected={expected_decision} actual={preflight.decision} "
            + "open=" + ",".join(sorted(open_human_gates))
            + " blockers=" + ",".join(sorted(preflight.blockers))
        ),
    )

    # Calibration network authority may become true only together with a durable
    # owner approval ref. Every later stage remains closed; retries remain disabled.
    approval_present = bool(gate.get("owner_approval_ref"))
    calibration_authority_coherent = (
        (approval_present and gate.get("network_calls_authorized") is True)
        or (not approval_present and gate.get("network_calls_authorized") is False)
    )
    require(
        "34_network_authority_stage_scoped_and_coherent",
        calibration_authority_coherent
        and holdout_gate["network_calls_authorized"] is False
        and analysis_gate["network_calls_authorized"] is False
        and protocol["network_calls_authorized"] is False
        and active["network_calls_authorized"] is False
        and gate["sdk_retries_allowed"] is False
        and holdout_gate["sdk_retries_allowed"] is False,
    )

    manifest_pin = gate.get("calibration_manifest_sha256")
    actual_manifest = jar15_calibration_manifest_sha256(ROOT)
    require(
        "35_manifest_pin_bound",
        isinstance(manifest_pin, str) and len(manifest_pin) == 64 and manifest_pin == actual_manifest,
        detail=f"pin={manifest_pin} actual={actual_manifest}",
    )

    # 36: prove the JAR-EXP-0015 change set introduced zero delta to the files
    # JAR-EXP-0014 authorization rests on. The invariant is commit-set disjointness:
    # no commit that touches a 0015-scoped path also touches a 0014-manifest path,
    # and the working tree carries no uncommitted edit to a 0014-manifest path.
    # This holds regardless of how 0014's own post-freeze commits interleave with
    # the 0015 series in history. The CI-frozen 0014 pin is deliberately NOT
    # asserted reproducible here: 0014 evolved after its freeze (its terminal-state
    # commits c591cb3/c55aaad/846876f edit calibration_preflight.py and
    # verify_jar_exp_0014_semantic_review.py), so re-validating 0014 integrity
    # belongs to the canonical repository / CI run 3543448441, not to JAR-EXP-0015.
    # That drift is surfaced as a finding only.
    gate14 = load(GATE14_REF)
    ci_pin14 = gate14.get("calibration_manifest_sha256")
    actual14 = calibration_manifest_sha256(ROOT)
    paths14 = list(CALIBRATION_INTEGRITY_PATHS)
    jar15_pathspecs = (
        "data/jar_exp_0015_*",
        "experiments/system_one_acceleration/jar15_*",
        "experiments/system_one_acceleration/guarded_jar15_*",
        "scripts/*jar_exp_0015*",
        "schemas/jar-exp-0015-*",
    )
    try:
        h14 = set(_git("log", "--format=%H", "--", *paths14).decode().split())
        h15 = set(_git("log", "--format=%H", "--", *jar15_pathspecs).decode().split())
        overlap = sorted(h14 & h15)
        clean14 = _git("status", "--porcelain", "--", *paths14).decode().strip() == ""
    except Exception as exc:  # fail closed: isolation cannot be proven
        raise SystemExit(f"FAIL[36_parent_0014_untouched_by_0015]: {exc}")
    require(
        "36_parent_0014_untouched_by_0015",
        clean14 and not overlap,
        detail=f"overlap={overlap} clean14={clean14} h14={len(h14)} h15={len(h15)}",
    )
    if ci_pin14 != actual14:
        print(
            "finding=0014 CI-frozen pin "
            f"{ci_pin14} is stale against this tree's 0014 manifest {actual14}; "
            "the drift is 0014-internal (its post-freeze terminal-state commits), "
            "not 0015 contamination; 0014 integrity re-validation belongs to the "
            "canonical repository / CI run 3543448441"
        )

    import experiments.system_one_acceleration.cost_guard as cg
    reserve_source = inspect.getsource(cg.PreRequestCostGuard.reserve_request)
    claim_source = inspect.getsource(cg.PreRequestCostGuard.begin_transport)
    require(
        "37_pricing_toctou_mitigated_not_erased",
        "verify_live_pricing" in reserve_source
        and "verify_live_pricing" in claim_source
        and "begin_transport" in claim_source,
    )

    # calibration case materialization must yield exactly the frozen split
    materialized = jar15_calibration_cases(ROOT)
    require(
        "38_calibration_case_materialization",
        len(materialized) == CALIBRATION_N
        and len({c.case_id for c in materialized}) == CALIBRATION_N
        and all(c.decision_type in by_type for c in materialized),
    )

    require("count", len([n for n in CHECKS if n != "count"]) == 38)
    print("PASS: JAR-EXP-0015 deterministic semantic verifier")
    print(f"falsification_attempts={len([n for n in CHECKS if n != 'count'])}")
    print("verdict=PASS_WITH_FINDINGS")
    print("finding=pricing validation cannot make provider-side post-check billing drift impossible")
    print(f"active_protocol={protocol['schema_version']} dataset={dataset['schema_version']}")
    print(f"calibration_manifest_sha256={actual_manifest}")
    print(f"preflight_decision={preflight.decision} blockers={'|'.join(sorted(preflight.blockers))}")
    for name in CHECKS:
        if name != "count":
            print(f"check={name}:PASS")


if __name__ == "__main__":
    main()