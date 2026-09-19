"""Deterministic zero-network preflight for JAR-EXP-0014."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


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

    if not gate.get("calibration_receipt_ref"):
        blockers.append("calibration_not_recorded")

    if not gate.get("execution_approval_ref"):
        blockers.append("execution_approval_not_recorded")
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
