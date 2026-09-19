"""Fail-closed zero-network calibration authorization for JAR-EXP-0014."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .corpus import build_calibration_corpus
from .cost_guard import CostGuardError, load_pricing_spec
from .integrity import calibration_manifest_sha256


@dataclass(frozen=True)
class CalibrationPreflightResult:
    decision: str
    blockers: tuple[str, ...]
    maximum_calls: int | None = None
    maximum_cost_usd: float | None = None
    requested_model: str | None = None


_CONCRETE_JEV_MODEL = re.compile(r"^jev-\d+\.\d+\.\d+$")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_concrete_jev_model(value: Any) -> bool:
    return isinstance(value, str) and bool(_CONCRETE_JEV_MODEL.fullmatch(value.strip()))


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

    contracts_path = root / "data" / "jar_exp_0014_question_contracts_v01.json"
    if not contracts_path.exists():
        blockers.append("calibration_question_contracts_missing")
    else:
        try:
            contracts_document = _load(contracts_path)
        except (OSError, json.JSONDecodeError):
            blockers.append("calibration_question_contracts_invalid_json")
        else:
            if contracts_document.get("status") != "FROZEN_PRECALIBRATION":
                blockers.append("calibration_question_contracts_not_frozen")

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
    max_calls = gate.get("max_provider_calls")
    max_cost = gate.get("max_cost_usd")

    if gate.get("status") == "CALIBRATION_COMPLETE_NO_THRESHOLD":
        return CalibrationPreflightResult(
            "NO_GO",
            ("calibration_already_completed",),
            maximum_calls=max_calls if isinstance(max_calls, int) and not isinstance(max_calls, bool) else None,
            maximum_cost_usd=float(max_cost)
            if isinstance(max_cost, (int, float)) and not isinstance(max_cost, bool) and max_cost > 0
            else None,
            requested_model=requested_model
            if isinstance(requested_model, str) and requested_model.strip()
            else None,
        )
    if not isinstance(requested_model, str) or not requested_model.strip():
        blockers.append("calibration_requested_model_missing")
    elif not _is_concrete_jev_model(requested_model):
        blockers.append("calibration_requested_model_not_pinned")

    pricing_spec = None
    pricing_ref = gate.get("pricing_spec_ref")
    pricing_path = _safe_ref(root, pricing_ref)
    if pricing_path is None:
        blockers.append("calibration_pricing_spec_ref_invalid")
    elif not pricing_path.exists():
        blockers.append("calibration_pricing_spec_missing")
    else:
        try:
            pricing_spec = load_pricing_spec(pricing_path)
        except (OSError, json.JSONDecodeError, CostGuardError):
            blockers.append("calibration_pricing_spec_invalid")
        else:
            if pricing_spec.model_id != requested_model:
                blockers.append("calibration_pricing_model_mismatch")

    if gate.get("cost_guard_mode") != "worst_case_context_write_ahead_v1":
        blockers.append("calibration_cost_hard_stop_unavailable")

    expected_calls = len(build_calibration_corpus())
    if not isinstance(max_calls, int) or isinstance(max_calls, bool) or max_calls < expected_calls:
        blockers.append("calibration_provider_call_ceiling_insufficient")

    manifest_pin = gate.get("calibration_manifest_sha256")
    if not isinstance(manifest_pin, str) or len(manifest_pin) != 64:
        blockers.append("calibration_manifest_not_frozen")
    else:
        try:
            actual_manifest = calibration_manifest_sha256(root)
        except (OSError, ValueError):
            blockers.append("calibration_manifest_unavailable")
        else:
            if actual_manifest != manifest_pin:
                blockers.append("calibration_manifest_mismatch")

    if (
        not isinstance(max_cost, (int, float))
        or isinstance(max_cost, bool)
        or max_cost <= 0
    ):
        blockers.append("calibration_cost_ceiling_not_frozen")
    elif pricing_spec is not None:
        approved_microusd = int(
            (Decimal(str(max_cost)) * Decimal(1_000_000)).to_integral_value()
        )
        required_microusd = (
            expected_calls * pricing_spec.max_request_cost_microusd
        )
        if approved_microusd < required_microusd:
            blockers.append("calibration_cost_ceiling_insufficient_for_hard_stop")

    review_ref = gate.get("semantic_review_ref")
    if not review_ref:
        blockers.append("calibration_semantic_review_not_recorded")
    else:
        review_path = _safe_ref(root, review_ref)
        if review_path is None:
            blockers.append("calibration_semantic_review_ref_invalid")
        elif not review_path.exists():
            blockers.append("calibration_semantic_review_missing")
        else:
            try:
                review = _load(review_path)
            except (OSError, json.JSONDecodeError):
                blockers.append("calibration_semantic_review_invalid_json")
            else:
                if review.get("schema_version") != "aftergraph.system-one-semantic-review/0.1":
                    blockers.append("calibration_semantic_review_schema_invalid")
                if review.get("experiment_id") != "JAR-EXP-0014":
                    blockers.append("calibration_semantic_review_experiment_mismatch")
                if review.get("verdict") not in {"PASS", "PASS_WITH_FINDINGS"}:
                    blockers.append("calibration_semantic_review_not_passed")
                if review.get("independent") is not True:
                    blockers.append("calibration_semantic_review_not_independent")
                if review.get("calibration_manifest_sha256") != manifest_pin:
                    blockers.append("calibration_semantic_review_manifest_mismatch")
                attempts = review.get("falsification_attempts_considered")
                if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 18:
                    blockers.append("calibration_semantic_review_falsification_incomplete")
                reviewer = review.get("reviewer")
                if not isinstance(reviewer, str) or not reviewer.strip():
                    blockers.append("calibration_semantic_review_reviewer_missing")
                evidence_ref = review.get("evidence_ref")
                if not isinstance(evidence_ref, str) or not evidence_ref.strip():
                    blockers.append("calibration_semantic_review_evidence_missing")
                _valid_attribution(
                    {"approved_by": reviewer, "approved_at": review.get("reviewed_at")},
                    blockers,
                )

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
                if approval.get("calibration_manifest_sha256") != manifest_pin:
                    blockers.append("calibration_approval_manifest_mismatch")
                if approval.get("max_provider_calls") != max_calls:
                    blockers.append("calibration_approval_call_ceiling_mismatch")
                if approval.get("max_cost_usd") != max_cost:
                    blockers.append("calibration_approval_cost_ceiling_mismatch")
                _valid_attribution(approval, blockers)

    if gate.get("network_calls_authorized") is not True:
        blockers.append("calibration_network_calls_not_authorized")

    return CalibrationPreflightResult(
        "READY_TO_CALIBRATE" if not blockers else "NO_GO",
        tuple(blockers),
        maximum_calls=max_calls if isinstance(max_calls, int) and not isinstance(max_calls, bool) else None,
        maximum_cost_usd=float(max_cost)
        if isinstance(max_cost, (int, float)) and not isinstance(max_cost, bool) and max_cost > 0
        else None,
        requested_model=requested_model
        if isinstance(requested_model, str) and requested_model.strip()
        else None,
    )
