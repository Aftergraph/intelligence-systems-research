"""Guarded calibration entrypoint for JAR-EXP-0014."""

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .calibration_preflight import evaluate_calibration_preflight
from .calibration_receipt import canonical_sha256
from .calibration_runner import CalibrationRunResult
from .durable_calibration import calibration_checkpoint_path, run_durable_calibration
from .client import TypeSafeBoundaryError, load_frozen_contracts
from .corpus import build_calibration_corpus
from .cost_guard import build_calibration_cost_guard, calibration_budget_ledger_path


class CalibrationAuthorizationError(RuntimeError):
    pass


def run_authorized_calibration(
    *,
    root: Path,
    client: Any,
    sdk: Any,
    contracts: Mapping[str, Mapping[str, Any]],
    pricing_fetcher: Callable[[str], str] | None = None,
) -> CalibrationRunResult:
    preflight = evaluate_calibration_preflight(root)
    if preflight.decision != "READY_TO_CALIBRATE":
        raise CalibrationAuthorizationError(
            "calibration not authorized: " + ", ".join(preflight.blockers)
        )
    if preflight.maximum_calls is None:
        raise CalibrationAuthorizationError("calibration provider-call ceiling unavailable")
    if preflight.maximum_cost_usd is None:
        raise CalibrationAuthorizationError("calibration cost ceiling unavailable")
    if preflight.requested_model is None:
        raise CalibrationAuthorizationError("calibration requested model unavailable")

    contracts_path = (
        Path(root) / "data" / "jar_exp_0014_question_contracts_v01.json"
    )
    try:
        frozen_contracts = load_frozen_contracts(contracts_path)
    except (OSError, json.JSONDecodeError, TypeSafeBoundaryError) as exc:
        raise CalibrationAuthorizationError(
            "frozen calibration contracts unavailable"
        ) from exc

    if canonical_sha256(dict(contracts)) != canonical_sha256(frozen_contracts):
        raise CalibrationAuthorizationError(
            "calibration contracts do not match frozen question contracts"
        )

    cost_guard = build_calibration_cost_guard(
        root=root,
        ledger_path=calibration_budget_ledger_path(),
        approved_budget_usd=preflight.maximum_cost_usd,
        pricing_fetcher=pricing_fetcher,
    )
    if cost_guard.spec.model_id != preflight.requested_model:
        raise CalibrationAuthorizationError("pricing model drift after preflight")

    return run_durable_calibration(
        client=client,
        sdk=sdk,
        requested_model=preflight.requested_model,
        contracts=contracts,
        cases=build_calibration_corpus(),
        maximum_calls=preflight.maximum_calls,
        cost_guard=cost_guard,
        checkpoint_path=calibration_checkpoint_path(),
    )
