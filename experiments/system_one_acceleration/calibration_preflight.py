"""Fail-closed zero-network calibration authorization for JAR-EXP-0014."""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping

from .corpus import build_calibration_corpus


@dataclass(frozen=True)
class CalibrationPreflightResult:
    decision: str
    blockers: tuple[str, ...]
    maximum_calls: int | None = None
    maximum_cost_usd: float | None = None


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


def _valid_attribution(approval: Mapping[str, Any], blockers: list[str]) -> None:
    principal = approval.get("approved_by")
    if not isinstance(principal, str) or not principal.strip():
        blockers.append("calibration_approval_principal_missing")

    timestamp = approval.get("approved_at")
    if not isinstance(timestamp, str) or not timestamp.strip():
        blockers.append("calibration_approval_timestamp_missing")
        return
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        blockers.append("calibration_approval_timestamp_invalid")
        return
    if parsed.tzinfo is None:
        blockers.append("calibration_approval_timestamp_not_timezone_aware")


def evaluate_calibration_preflight(root: Path) -> CalibrationPreflightResult:
    """Verify bounded calibration authorization without SDK imports or network access."""
    root = Path(root)
    blockers: list[str] = []

    protocol_path = root / "data" / "jar_exp_0014_calibration_protocol_v01.json"
    if not protocol_path.exists():
        blockers.append("calibration_protocol_missing")
    else:
        try:
            protocol = _load(protocol_path)
        except (OSError, json.JSONDecodeError):
            blockers.append("calibration_protocol_invalid_json")
        else:
            if protocol.get("status") != "FROZEN_PRECALIBRATION":
                blockers.append("calibration_protocol_not_frozen")
            if protocol.get("live_execution_authorized") is not False:
                blockers.append("calibration_protocol_authorization_drift")

    gate_path = root / "data" / "jar_exp_0014_calibration_gate_v01.json"
    if not gate_path.exists():
        blockers.append("calibration_gate_missing")
        return CalibrationPreflightResult("NO_GO", tuple(blockers))
    try:
        gate = _load(gate_path)
    except (OSError, json.JSONDecodeError):
        blockers.append("calibration_gate_invalid_json")
        return CalibrationPreflightResult("NO_GO", tuple(blockers))

    if gate.get("schema_version") != "jar-exp-0014.calibration-gate/0.1":
        blockers.append("calibration_gate_schema_invalid")
    if gate.get("experiment_id") != "JAR-EXP-0014":
        blockers.append("calibration_gate_experiment_mismatch")

    requested_model = gate.get("requested_typesafe_model")
    if not isinstance(requested_model, str) or not requested_model.strip():
        blockers.append("calibration_requested_model_missing")

    expected_calls = len(build_calibration_corpus())
    max_calls = gate.get("max_provider_calls")
    if not isinstance(max_calls, int) or isinstance(max_calls, bool) or max_calls < expected_calls:
        blockers.append("calibration_provider_call_ceiling_insufficient")

    max_cost = gate.get("max_cost_usd")
    if (
        not isinstance(max_cost, (int, float))
        or isinstance(max_cost, bool)
        or max_cost <= 0
    ):
        blockers.append("calibration_cost_ceiling_not_frozen")

    approval_ref = gate.get("calibration_approval_ref")
    if not approval_ref:
        blockers.append("calibration_approval_not_recorded")
    else:
        approval_path = _safe_ref(root, approval_ref)
        if approval_path is None:
            blockers.append("calibration_approval_ref_invalid")
        elif not approval_path.exists():
            blockers.append("calibration_approval_missing")
        else:
            try:
                approval = _load(approval_path)
            except (OSError, json.JSONDecodeError):
                blockers.append("calibration_approval_invalid_json")
            else:
                if approval.get("schema_version") != "aftergraph.system-one-calibration-approval/0.1":
                    blockers.append("calibration_approval_schema_invalid")
                if approval.get("experiment_id") != "JAR-EXP-0014":
                    blockers.append("calibration_approval_experiment_mismatch")
                if approval.get("approved") is not True:
                    blockers.append("calibration_approval_not_granted")
                if approval.get("network_calls_authorized") is not True:
                    blockers.append("calibration_approval_network_scope_missing")
                if approval.get("requested_typesafe_model") != requested_model:
                    blockers.append("calibration_approval_model_mismatch")
                if approval.get("max_provider_calls") != max_calls:
                    blockers.append("calibration_approval_call_ceiling_mismatch")
                if approval.get("max_cost_usd") != max_cost:
                    blockers.append("calibration_approval_cost_ceiling_mismatch")
                _valid_attribution(approval, blockers)

    if gate.get("network_calls_authorized") is not True:
        blockers.append("calibration_network_calls_not_authorized")

    # TypeSafe currently exposes usage after a request, but no repository-verified
    # native pre-request spend/token hard cap. A provider-call ceiling is not a
    # dollar hard stop, so live calibration remains impossible until a technical
    # cost enforcement mechanism is implemented and independently verified.
    blockers.append("calibration_cost_hard_stop_unavailable")

    return CalibrationPreflightResult(
        "READY_TO_CALIBRATE" if not blockers else "NO_GO",
        tuple(blockers),
        maximum_calls=max_calls if isinstance(max_calls, int) and not isinstance(max_calls, bool) else None,
        maximum_cost_usd=float(max_cost)
        if isinstance(max_cost, (int, float)) and not isinstance(max_cost, bool) and max_cost > 0
        else None,
    )
