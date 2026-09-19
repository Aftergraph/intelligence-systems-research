"""Guarded calibration entrypoint for JAR-EXP-0015 (Amendment-004 activation).

This module owns the 0015-specific durable budget namespace. The shared
``cost_guard``/``durable_calibration`` primitives are reused unmodified because
they are pinned inside the frozen JAR-EXP-0014 integrity manifest; editing them
would disturb the 0014 record. Instead, every 0015 durable path (SQLite ledger
and JSON checkpoint) and the ledger run_id are namespaced under ``jar-exp-0015``
so a 0015 run can never read, write, or double-spend the 0014 budget.
"""

from decimal import Decimal, ROUND_FLOOR
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .calibration_runner import CalibrationRunResult
from .client import TypeSafeBoundaryError, load_frozen_contracts
from .corpus import CalibrationCase
from .cost_guard import BudgetLedger, PreRequestCostGuard
from .durable_calibration import run_durable_calibration
from .jar15_analysis import canonical_sha256
from .jar15_calibration_preflight import (
    Jar15CalibrationPreflightResult,
    evaluate_jar15_calibration_preflight,
)
from .jar15_pricing import load_jar15_pricing_spec

JAR15_RUN_ID = "JAR-EXP-0015-calibration-v04"
JAR15_PRICING_REF = "data/jar_exp_0015_typesafe_pricing_v01.json"
JAR15_CONTRACTS_REF = "data/jar_exp_0015_question_contracts_v01.json"
JAR15_DATASET_REF = "data/jar_exp_0015_dataset_v03.json"
JAR15_CALIBRATION_N = 1952


class Jar15CalibrationAuthorizationError(RuntimeError):
    pass


def jar15_calibration_ledger_path() -> Path:
    """Canonical durable 0015 ledger path, namespaced away from the 0014 budget."""
    return (
        Path.home()
        / ".aftergraph"
        / "research"
        / "jar-exp-0015"
        / "calibration-budget-v04.sqlite"
    )


def jar15_calibration_checkpoint_path() -> Path:
    """Canonical durable 0015 checkpoint path, namespaced away from 0014."""
    return (
        Path.home()
        / ".aftergraph"
        / "research"
        / "jar-exp-0015"
        / "calibration-checkpoint-v04.json"
    )


def jar15_calibration_cases(root: Path) -> list[CalibrationCase]:
    """Materialize the frozen 1,952 calibration-split cases from dataset v0.3."""
    dataset = json.loads((Path(root) / JAR15_DATASET_REF).read_text(encoding="utf-8"))
    if dataset.get("schema_version") != "jar-exp-0015.dataset/0.3":
        raise Jar15CalibrationAuthorizationError("dataset v0.3 schema mismatch")
    if dataset.get("status") != "FROZEN_PREEXECUTION":
        raise Jar15CalibrationAuthorizationError("dataset v0.3 is not frozen")
    rows = dataset.get("cases")
    if not isinstance(rows, list):
        raise Jar15CalibrationAuthorizationError("dataset v0.3 cases invalid")

    cases: list[CalibrationCase] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("split") != "calibration":
            continue
        case_id = row.get("case_id")
        decision_type = row.get("decision_type")
        state = row.get("state")
        if (
            not isinstance(case_id, str)
            or not isinstance(decision_type, str)
            or not isinstance(state, dict)
        ):
            raise Jar15CalibrationAuthorizationError("calibration case shape invalid")
        cases.append(
            CalibrationCase(
                case_id=case_id,
                decision_type=decision_type,
                state=state,
                expected=row.get("expected"),
                critical=bool(row.get("critical")),
            )
        )
    if len(cases) != JAR15_CALIBRATION_N:
        raise Jar15CalibrationAuthorizationError(
            f"calibration split cardinality mismatch: {len(cases)} != {JAR15_CALIBRATION_N}"
        )
    if len({case.case_id for case in cases}) != JAR15_CALIBRATION_N:
        raise Jar15CalibrationAuthorizationError("calibration case ids not unique")
    return cases


def build_jar15_calibration_cost_guard(
    *,
    root: Path,
    ledger_path: Path,
    approved_budget_usd: float,
    pricing_fetcher: Callable[[str], str] | None = None,
) -> PreRequestCostGuard:
    spec = load_jar15_pricing_spec(Path(root) / JAR15_PRICING_REF)
    approved_microusd = int(
        (Decimal(str(approved_budget_usd)) * Decimal(1_000_000)).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    ledger = BudgetLedger(
        ledger_path,
        run_id=JAR15_RUN_ID,
        approved_budget_microusd=approved_microusd,
        pricing_spec_sha256=spec.canonical_sha256,
    )
    return PreRequestCostGuard(
        spec=spec, ledger=ledger, pricing_fetcher=pricing_fetcher
    )


def run_authorized_jar15_calibration(
    *,
    root: Path,
    client: Any,
    sdk: Any,
    contracts: Mapping[str, Mapping[str, Any]],
    pricing_fetcher: Callable[[str], str] | None = None,
    preflight: Jar15CalibrationPreflightResult | None = None,
) -> CalibrationRunResult:
    """Execute bounded 0015 calibration only after the fail-closed preflight passes."""
    result = preflight or evaluate_jar15_calibration_preflight(Path(root))
    if result.decision != "READY_TO_CALIBRATE":
        raise Jar15CalibrationAuthorizationError(
            "calibration not authorized: " + ", ".join(result.blockers)
        )
    if result.maximum_calls is None:
        raise Jar15CalibrationAuthorizationError("calibration provider-call ceiling unavailable")
    if result.maximum_cost_usd is None:
        raise Jar15CalibrationAuthorizationError("calibration cost ceiling unavailable")
    if result.requested_model is None:
        raise Jar15CalibrationAuthorizationError("calibration requested model unavailable")

    try:
        frozen_contracts = load_frozen_contracts(Path(root) / JAR15_CONTRACTS_REF)
    except (OSError, json.JSONDecodeError, TypeSafeBoundaryError) as exc:
        raise Jar15CalibrationAuthorizationError(
            "frozen calibration contracts unavailable"
        ) from exc

    if canonical_sha256(dict(contracts)) != canonical_sha256(frozen_contracts):
        raise Jar15CalibrationAuthorizationError(
            "calibration contracts do not match frozen question contracts"
        )

    cost_guard = build_jar15_calibration_cost_guard(
        root=root,
        ledger_path=jar15_calibration_ledger_path(),
        approved_budget_usd=result.maximum_cost_usd,
        pricing_fetcher=pricing_fetcher,
    )
    if cost_guard.spec.model_id != result.requested_model:
        raise Jar15CalibrationAuthorizationError("pricing model drift after preflight")

    return run_durable_calibration(
        client=client,
        sdk=sdk,
        requested_model=result.requested_model,
        contracts=contracts,
        cases=jar15_calibration_cases(Path(root)),
        maximum_calls=result.maximum_calls,
        cost_guard=cost_guard,
        checkpoint_path=jar15_calibration_checkpoint_path(),
    )