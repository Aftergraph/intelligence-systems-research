"""Deterministic zero-network preflight for JAR-EXP-0014."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class PreflightResult:
    decision: str
    blockers: tuple[str, ...]


REQUIRED_FROZEN_FILES = (
    "data/jar_exp_0014_question_contracts_v01.json",
    "data/jar_exp_0014_workload_plan_v01.json",
    "data/jar_exp_0014_critical_risk_pack_v01.json",
    "data/jar_exp_0014_randomization_v01.json",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_ref(root: Path, ref: Any) -> Path | None:
    if not isinstance(ref, str) or not ref.strip():
        return None
    root_resolved = root.resolve()
    candidate = (root / ref).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None
    return candidate


def _validate_calibration_receipt(
    root: Path, gate: Mapping[str, Any], blockers: list[str]
) -> None:
    ref = gate.get("calibration_receipt_ref")
    if not ref:
        blockers.append("calibration_not_recorded")
        return

    path = _safe_ref(root, ref)
    if path is None:
        blockers.append("calibration_receipt_ref_invalid")
        return
    if not path.exists():
        blockers.append("calibration_receipt_missing")
        return
    try:
        receipt = _load(path)
    except (OSError, json.JSONDecodeError):
        blockers.append("calibration_receipt_invalid_json")
        return

    if receipt.get("schema_version") != "aftergraph.system-one-calibration/0.1":
        blockers.append("calibration_receipt_schema_invalid")
    if receipt.get("experiment_id") != "JAR-EXP-0014":
        blockers.append("calibration_receipt_experiment_mismatch")
    if receipt.get("returned_model") != gate.get("returned_typesafe_model_pin"):
        blockers.append("calibration_model_pin_mismatch")

    result = receipt.get("result")
    if not isinstance(result, Mapping):
        blockers.append("calibration_receipt_result_invalid")
        return

    threshold = gate.get("cascade_confidence_threshold")
    if result.get("threshold") != threshold:
        blockers.append("calibration_threshold_mismatch")
    if result.get("feasible") is not True:
        blockers.append("calibration_not_feasible")
    if result.get("critical_errors") != 0:
        blockers.append("calibration_critical_error")
    total = result.get("total")
    critical_cases = result.get("critical_cases")
    if not isinstance(total, int) or isinstance(total, bool) or total < 128:
        blockers.append("calibration_sample_too_small")
    if (
        not isinstance(critical_cases, int)
        or isinstance(critical_cases, bool)
        or critical_cases < 30
    ):
        blockers.append("calibration_critical_pack_incomplete")


def _validate_execution_approval(
    root: Path, gate: Mapping[str, Any], blockers: list[str]
) -> None:
    ref = gate.get("execution_approval_ref")
    if not ref:
        blockers.append("execution_approval_not_recorded")
        return
    path = _safe_ref(root, ref)
    if path is None:
        blockers.append("execution_approval_ref_invalid")
    elif not path.exists():
        blockers.append("execution_approval_missing")


def evaluate_preflight(root: Path) -> PreflightResult:
    """Evaluate readiness without importing SDKs or making network calls."""
    root = Path(root)
    blockers: list[str] = []

    for rel in REQUIRED_FROZEN_FILES:
        path = root / rel
        if not path.exists():
            blockers.append(f"missing:{rel}")
            continue
        try:
            data = _load(path)
        except (OSError, json.JSONDecodeError):
            blockers.append(f"invalid_json:{rel}")
            continue
        if data.get("status") != "FROZEN_PRECALIBRATION":
            blockers.append(f"not_frozen:{rel}")

    gate_path = root / "data" / "jar_exp_0014_execution_gate_v01.json"
    if not gate_path.exists():
        blockers.append("missing:execution_gate")
        return PreflightResult("NO_GO", tuple(blockers))

    gate = _load(gate_path)

    if not gate.get("returned_typesafe_model_pin"):
        blockers.append("typesafe_model_not_pinned")
    if not gate.get("control_model_pin"):
        blockers.append("control_model_not_pinned")

    threshold = gate.get("cascade_confidence_threshold")
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        blockers.append("cascade_threshold_not_frozen")
    elif not 0.0 <= float(threshold) <= 1.0:
        blockers.append("cascade_threshold_invalid")

    _validate_calibration_receipt(root, gate, blockers)
    _validate_execution_approval(root, gate, blockers)
    if gate.get("network_calls_authorized") is not True:
        blockers.append("network_calls_not_authorized")
    if gate.get("confirmatory_execution_authorized") is not True:
        blockers.append("confirmatory_execution_not_authorized")

    max_cost = gate.get("max_cost_usd")
    if not isinstance(max_cost, (int, float)) or isinstance(max_cost, bool) or max_cost <= 0:
        blockers.append("cost_ceiling_not_frozen")

    max_calls = gate.get("max_provider_calls")
    if not isinstance(max_calls, int) or isinstance(max_calls, bool) or max_calls <= 0:
        blockers.append("provider_call_ceiling_not_frozen")

    return PreflightResult(
        "READY_TO_EXECUTE" if not blockers else "NO_GO",
        tuple(blockers),
    )
