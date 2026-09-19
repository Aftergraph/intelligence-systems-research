"""Guarded calibration entrypoint for JAR-EXP-0014.

This is the only repository-provided composition path from authorization evidence
to the network-capable calibration runner. The injected client owns transport;
this wrapper refuses to call it unless calibration preflight is READY.
"""

import json
from pathlib import Path
from typing import Any, Mapping

from .calibration_preflight import evaluate_calibration_preflight
from .calibration_receipt import canonical_sha256
from .calibration_runner import CalibrationRunResult, run_calibration
from .corpus import build_calibration_corpus


class CalibrationAuthorizationError(RuntimeError):
    pass


def run_authorized_calibration(
    *,
    root: Path,
    client: Any,
    sdk: Any,
    contracts: Mapping[str, Mapping[str, Any]],
) -> CalibrationRunResult:
    preflight = evaluate_calibration_preflight(root)
    if preflight.decision != "READY_TO_CALIBRATE":
        raise CalibrationAuthorizationError(
            "calibration not authorized: " + ", ".join(preflight.blockers)
        )
    if preflight.maximum_calls is None:
        raise CalibrationAuthorizationError("calibration provider-call ceiling unavailable")
    if preflight.requested_model is None:
        raise CalibrationAuthorizationError("calibration requested model unavailable")

    contracts_path = (
        Path(root) / "data" / "jar_exp_0014_question_contracts_v01.json"
    )
    try:
        frozen_document = json.loads(contracts_path.read_text(encoding="utf-8"))
        frozen_contracts = frozen_document["contracts"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise CalibrationAuthorizationError(
            "frozen calibration contracts unavailable"
        ) from exc

    if canonical_sha256(dict(contracts)) != canonical_sha256(frozen_contracts):
        raise CalibrationAuthorizationError(
            "calibration contracts do not match frozen question contracts"
        )

    return run_calibration(
        client=client,
        sdk=sdk,
        requested_model=preflight.requested_model,
        contracts=contracts,
        cases=build_calibration_corpus(),
        maximum_calls=preflight.maximum_calls,
    )
