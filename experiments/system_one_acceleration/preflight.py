"""Deterministic zero-network preflight for JAR-EXP-0014."""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping

from .calibration_receipt import calibration_corpus_sha256, canonical_sha256
from .corpus import build_calibration_corpus
from .integrity import execution_manifest_sha256


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
    if receipt.get("requested_model") != gate.get("requested_typesafe_model"):
        blockers.append("calibration_requested_model_mismatch")
    if receipt.get("returned_model") != gate.get("returned_typesafe_model_pin"):
        blockers.append("calibration_model_pin_mismatch")

    expected_corpus_hash = calibration_corpus_sha256(build_calibration_corpus())
    if receipt.get("corpus_sha256") != expected_corpus_hash:
        blockers.append("calibration_corpus_hash_mismatch")

    protocol_path = root / "data" / "jar_exp_0014_calibration_protocol_v01.json"
    if not protocol_path.exists():
        blockers.append("calibration_protocol_missing")
    else:
        try:
            protocol = _load(protocol_path)
        except (OSError, json.JSONDecodeError):
            blockers.append("calibration_protocol_invalid_json")
        else:
            if receipt.get("protocol_sha256") != canonical_sha256(protocol):
                blockers.append("calibration_protocol_hash_mismatch")

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

    usage = receipt.get("usage")
    if not isinstance(usage, Mapping):
        blockers.append("calibration_usage_invalid")
    else:
        provider_calls = usage.get("provider_calls")
        if (
            not isinstance(provider_calls, int)
            or isinstance(provider_calls, bool)
            or provider_calls != total
        ):
            blockers.append("calibration_provider_call_count_mismatch")


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
        return
    if not path.exists():
        blockers.append("execution_approval_missing")
        return
    try:
        approval = _load(path)
    except (OSError, json.JSONDecodeError):
        blockers.append("execution_approval_invalid_json")
        return

    if approval.get("schema_version") != "aftergraph.system-one-execution-approval/0.1":
        blockers.append("execution_approval_schema_invalid")
    if approval.get("experiment_id") != "JAR-EXP-0014":
        blockers.append("execution_approval_experiment_mismatch")
    approved_by = approval.get("approved_by")
    if not isinstance(approved_by, str) or not approved_by.strip():
        blockers.append("execution_approval_principal_missing")

    approved_at = approval.get("approved_at")
    if not isinstance(approved_at, str) or not approved_at.strip():
        blockers.append("execution_approval_timestamp_missing")
    else:
        try:
            parsed_approved_at = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
        except ValueError:
            blockers.append("execution_approval_timestamp_invalid")
        else:
            if parsed_approved_at.tzinfo is None:
                blockers.append("execution_approval_timestamp_not_timezone_aware")

    if approval.get("approved") is not True:
        blockers.append("execution_approval_not_granted")
    if approval.get("network_calls_authorized") is not True:
        blockers.append("approval_network_scope_missing")
    if approval.get("confirmatory_execution_authorized") is not True:
        blockers.append("approval_confirmatory_scope_missing")
    if approval.get("returned_typesafe_model_pin") != gate.get("returned_typesafe_model_pin"):
        blockers.append("approval_typesafe_model_mismatch")
    if approval.get("control_model_pin") != gate.get("control_model_pin"):
        blockers.append("approval_control_model_mismatch")
    if approval.get("cascade_confidence_threshold") != gate.get(
        "cascade_confidence_threshold"
    ):
        blockers.append("approval_threshold_mismatch")
    if approval.get("max_cost_usd") != gate.get("max_cost_usd"):
        blockers.append("approval_cost_ceiling_mismatch")
    if approval.get("max_provider_calls") != gate.get("max_provider_calls"):
        blockers.append("approval_call_ceiling_mismatch")
    if approval.get("execution_manifest_sha256") != gate.get(
        "execution_manifest_sha256"
    ):
        blockers.append("approval_execution_manifest_mismatch")


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

    execution_manifest_pin = gate.get("execution_manifest_sha256")
    if not isinstance(execution_manifest_pin, str) or len(execution_manifest_pin) != 64:
        blockers.append("execution_manifest_not_frozen")
    else:
        try:
            actual_execution_manifest = execution_manifest_sha256(root)
        except (OSError, ValueError):
            blockers.append("execution_manifest_unavailable")
        else:
            if actual_execution_manifest != execution_manifest_pin:
                blockers.append("execution_manifest_mismatch")

    if not gate.get("requested_typesafe_model"):
        blockers.append("typesafe_requested_model_missing")
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
