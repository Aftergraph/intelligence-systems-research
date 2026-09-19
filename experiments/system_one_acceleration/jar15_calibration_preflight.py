"""Fail-closed zero-network calibration authorization for JAR-EXP-0015.

Mirrors the JAR-EXP-0014 preflight but binds the Amendment-004 activation
(protocol v0.4 / dataset v0.3). No SDK import and no network access occur here;
every check is a deterministic read of frozen local artifacts. The preflight is
expected to return NO_GO until a content-addressed semantic review, an explicit
owner/network approval, and a frozen calibration-manifest pin are all present.
The owner/network approval is a human step this module must never fabricate.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .cost_guard import CostGuardError
from .jar15_integrity import jar15_calibration_manifest_sha256
from .jar15_pricing import load_jar15_pricing_spec

ACTIVE_PROTOCOL_REF = "data/jar_exp_0015_active_protocol.json"
PROTOCOL_REF = "data/jar_exp_0015_protocol_v04.json"
DATASET_REF = "data/jar_exp_0015_dataset_v03.json"
SPLIT_MANIFEST_REF = "data/jar_exp_0015_split_manifest_v03.json"
CONTRACTS_REF = "data/jar_exp_0015_question_contracts_v01.json"
GATE_REF = "data/jar_exp_0015_calibration_gate_v01.json"

MIN_FALSIFICATION_ATTEMPTS = 32

_CONCRETE_JEV_MODEL = re.compile(r"^jev-\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class Jar15CalibrationPreflightResult:
    decision: str
    blockers: tuple[str, ...]
    maximum_calls: int | None = None
    maximum_cost_usd: float | None = None
    requested_model: str | None = None


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


def _valid_attribution(document: dict[str, Any], blockers: list[str], prefix: str) -> None:
    principal = document.get("approved_by")
    if not isinstance(principal, str) or not principal.strip():
        blockers.append(f"{prefix}_principal_missing")

    timestamp = document.get("approved_at")
    if not isinstance(timestamp, str) or not timestamp.strip():
        blockers.append(f"{prefix}_timestamp_missing")
        return
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        blockers.append(f"{prefix}_timestamp_invalid")
        return
    if parsed.tzinfo is None:
        blockers.append(f"{prefix}_timestamp_not_timezone_aware")


def _int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _positive_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
        return float(value)
    return None


def evaluate_jar15_calibration_preflight(root: Path) -> Jar15CalibrationPreflightResult:
    """Verify bounded 0015 calibration authorization without SDK imports or network."""
    root = Path(root)
    blockers: list[str] = []

    # --- active registry pointer ---
    active = None
    active_path = root / ACTIVE_PROTOCOL_REF
    if not active_path.exists():
        blockers.append("jar15_active_protocol_missing")
    else:
        try:
            active = _load(active_path)
        except (OSError, json.JSONDecodeError):
            blockers.append("jar15_active_protocol_invalid_json")
        else:
            if active.get("status") != "ACTIVE_PREEXECUTION":
                blockers.append("jar15_active_protocol_not_active")
            if active.get("active_protocol_ref") != PROTOCOL_REF:
                blockers.append("jar15_active_protocol_pointer_drift")
            if active.get("active_dataset_ref") != DATASET_REF:
                blockers.append("jar15_active_dataset_pointer_drift")
            if active.get("active_split_manifest_ref") != SPLIT_MANIFEST_REF:
                blockers.append("jar15_active_manifest_pointer_drift")
            if active.get("network_calls_authorized") is not False:
                blockers.append("jar15_active_protocol_network_drift")

    # --- protocol v0.4 ---
    protocol = None
    protocol_path = root / PROTOCOL_REF
    if not protocol_path.exists():
        blockers.append("jar15_calibration_protocol_missing")
    else:
        try:
            protocol = _load(protocol_path)
        except (OSError, json.JSONDecodeError):
            blockers.append("jar15_calibration_protocol_invalid_json")
        else:
            if protocol.get("schema_version") != "jar-exp-0015.protocol/0.4":
                blockers.append("jar15_calibration_protocol_schema_invalid")
            if protocol.get("status") != "FROZEN_PREEXECUTION":
                blockers.append("jar15_calibration_protocol_not_frozen")
            if protocol.get("network_calls_authorized") is not False:
                blockers.append("jar15_calibration_protocol_authorization_drift")
            dataset_block = protocol.get("dataset")
            if not isinstance(dataset_block, dict):
                blockers.append("jar15_protocol_dataset_block_invalid")
            else:
                if dataset_block.get("dataset_ref") != DATASET_REF:
                    blockers.append("jar15_protocol_dataset_ref_drift")
                if dataset_block.get("split_manifest_ref") != SPLIT_MANIFEST_REF:
                    blockers.append("jar15_protocol_manifest_ref_drift")

    # --- frozen question contracts ---
    contracts_path = root / CONTRACTS_REF
    if not contracts_path.exists():
        blockers.append("jar15_question_contracts_missing")
    else:
        try:
            contracts_document = _load(contracts_path)
        except (OSError, json.JSONDecodeError):
            blockers.append("jar15_question_contracts_invalid_json")
        else:
            if contracts_document.get("status") != "FROZEN_PRECALIBRATION":
                blockers.append("jar15_question_contracts_not_frozen")

    # --- frozen dataset artifact: calibration cardinality + content hash ---
    dataset_sha = None
    expected_calls = None
    dataset_path = root / DATASET_REF
    if not dataset_path.exists():
        blockers.append("jar15_dataset_missing")
    else:
        try:
            dataset = _load(dataset_path)
        except (OSError, json.JSONDecodeError):
            blockers.append("jar15_dataset_invalid_json")
        else:
            dataset_sha = sha256(dataset_path.read_bytes()).hexdigest()
            if dataset.get("schema_version") != "jar-exp-0015.dataset/0.3":
                blockers.append("jar15_dataset_schema_invalid")
            if dataset.get("status") != "FROZEN_PREEXECUTION":
                blockers.append("jar15_dataset_not_frozen")
            cases = dataset.get("cases")
            if not isinstance(cases, list):
                blockers.append("jar15_dataset_cases_invalid")
            else:
                expected_calls = sum(
                    1
                    for row in cases
                    if isinstance(row, dict) and row.get("split") == "calibration"
                )

    # --- frozen split manifest content hash ---
    manifest_sha = None
    manifest_path = root / SPLIT_MANIFEST_REF
    if not manifest_path.exists():
        blockers.append("jar15_split_manifest_missing")
    else:
        manifest_sha = sha256(manifest_path.read_bytes()).hexdigest()

    # --- cross-bind dataset/manifest hashes across protocol + active registry ---
    if protocol is not None and isinstance(protocol.get("dataset"), dict):
        pds = protocol["dataset"]
        if dataset_sha is not None and pds.get("dataset_sha256") != dataset_sha:
            blockers.append("jar15_protocol_dataset_sha_drift")
        if manifest_sha is not None and pds.get("split_manifest_sha256") != manifest_sha:
            blockers.append("jar15_protocol_manifest_sha_drift")
    if active is not None:
        if dataset_sha is not None and active.get("active_dataset_sha256") != dataset_sha:
            blockers.append("jar15_active_dataset_sha_drift")
        if (
            manifest_sha is not None
            and active.get("active_split_manifest_sha256") != manifest_sha
        ):
            blockers.append("jar15_active_manifest_sha_drift")

    # --- calibration gate (fatal if unreadable) ---
    gate_path = root / GATE_REF
    if not gate_path.exists():
        blockers.append("jar15_calibration_gate_missing")
        return Jar15CalibrationPreflightResult("NO_GO", tuple(blockers))
    try:
        gate = _load(gate_path)
    except (OSError, json.JSONDecodeError):
        blockers.append("jar15_calibration_gate_invalid_json")
        return Jar15CalibrationPreflightResult("NO_GO", tuple(blockers))

    if gate.get("schema_version") != "jar-exp-0015.calibration-gate/0.1":
        blockers.append("jar15_calibration_gate_schema_invalid")
    if gate.get("experiment_id") != "JAR-EXP-0015":
        blockers.append("jar15_calibration_gate_experiment_mismatch")
    if gate.get("active_protocol_ref") != PROTOCOL_REF:
        blockers.append("jar15_gate_protocol_ref_drift")
    if gate.get("dataset_ref") != DATASET_REF:
        blockers.append("jar15_gate_dataset_ref_drift")
    if dataset_sha is not None and gate.get("dataset_sha256") != dataset_sha:
        blockers.append("jar15_gate_dataset_sha_drift")
    if gate.get("split") != "calibration":
        blockers.append("jar15_gate_split_invalid")

    requested_model = gate.get("requested_model")
    max_calls = gate.get("max_provider_calls")
    max_cost = gate.get("max_cost_usd")

    if gate.get("status") == "CALIBRATION_COMPLETE":
        return Jar15CalibrationPreflightResult(
            "NO_GO",
            ("jar15_calibration_already_completed",),
            maximum_calls=_int(max_calls),
            maximum_cost_usd=_positive_number(max_cost),
            requested_model=requested_model
            if isinstance(requested_model, str) and requested_model.strip()
            else None,
        )

    if not isinstance(requested_model, str) or not requested_model.strip():
        blockers.append("jar15_requested_model_missing")
    elif not _is_concrete_jev_model(requested_model):
        blockers.append("jar15_requested_model_not_pinned")

    # --- pricing spec ---
    pricing_spec = None
    pricing_path = _safe_ref(root, gate.get("pricing_spec_ref"))
    if pricing_path is None:
        blockers.append("jar15_pricing_spec_ref_invalid")
    elif not pricing_path.exists():
        blockers.append("jar15_pricing_spec_missing")
    else:
        try:
            pricing_spec = load_jar15_pricing_spec(pricing_path)
        except (OSError, json.JSONDecodeError, CostGuardError):
            blockers.append("jar15_pricing_spec_invalid")
        else:
            if pricing_spec.model_id != requested_model:
                blockers.append("jar15_pricing_model_mismatch")

    # --- provider-call ceiling ---
    if expected_calls is None:
        blockers.append("jar15_expected_calibration_count_unavailable")
    else:
        ceiling = _int(max_calls)
        if ceiling is None or ceiling < expected_calls:
            blockers.append("jar15_provider_call_ceiling_insufficient")
        split_case_count = _int(gate.get("split_case_count"))
        if split_case_count is not None and split_case_count != expected_calls:
            blockers.append("jar15_split_case_count_mismatch")

    # --- frozen calibration-manifest pin ---
    manifest_pin = gate.get("calibration_manifest_sha256")
    if not isinstance(manifest_pin, str) or len(manifest_pin) != 64:
        blockers.append("jar15_manifest_not_frozen")
    else:
        try:
            actual_manifest = jar15_calibration_manifest_sha256(root)
        except (OSError, ValueError):
            blockers.append("jar15_manifest_unavailable")
        else:
            if actual_manifest != manifest_pin:
                blockers.append("jar15_manifest_mismatch")

    # --- cost ceiling must cover the hard-stop reservation total ---
    positive_cost = _positive_number(max_cost)
    if positive_cost is None:
        blockers.append("jar15_cost_ceiling_not_frozen")
    elif pricing_spec is not None and expected_calls is not None:
        approved_microusd = int(
            (Decimal(str(max_cost)) * Decimal(1_000_000)).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        required_microusd = expected_calls * pricing_spec.max_request_cost_microusd
        if approved_microusd < required_microusd:
            blockers.append("jar15_cost_ceiling_insufficient_for_hard_stop")

    # --- content-addressed semantic review ---
    review_ref = gate.get("semantic_review_ref")
    if not review_ref:
        blockers.append("jar15_semantic_review_not_recorded")
    else:
        review_path = _safe_ref(root, review_ref)
        if review_path is None:
            blockers.append("jar15_semantic_review_ref_invalid")
        elif not review_path.exists():
            blockers.append("jar15_semantic_review_missing")
        else:
            try:
                review = _load(review_path)
            except (OSError, json.JSONDecodeError):
                blockers.append("jar15_semantic_review_invalid_json")
            else:
                if review.get("schema_version") != "aftergraph.system-one-semantic-review/0.1":
                    blockers.append("jar15_semantic_review_schema_invalid")
                if review.get("experiment_id") != "JAR-EXP-0015":
                    blockers.append("jar15_semantic_review_experiment_mismatch")
                if review.get("verdict") not in {"PASS", "PASS_WITH_FINDINGS"}:
                    blockers.append("jar15_semantic_review_not_passed")
                if review.get("independent") is not True:
                    blockers.append("jar15_semantic_review_not_independent")
                if review.get("calibration_manifest_sha256") != manifest_pin:
                    blockers.append("jar15_semantic_review_manifest_mismatch")
                attempts = _int(review.get("falsification_attempts_considered"))
                if attempts is None or attempts < MIN_FALSIFICATION_ATTEMPTS:
                    blockers.append("jar15_semantic_review_falsification_incomplete")
                reviewer = review.get("reviewer")
                if not isinstance(reviewer, str) or not reviewer.strip():
                    blockers.append("jar15_semantic_review_reviewer_missing")
                evidence_ref = review.get("evidence_ref")
                if not isinstance(evidence_ref, str) or not evidence_ref.strip():
                    blockers.append("jar15_semantic_review_evidence_missing")
                _valid_attribution(
                    {"approved_by": reviewer, "approved_at": review.get("reviewed_at")},
                    blockers,
                    "jar15_semantic_review",
                )

    # --- explicit owner/network approval (human step; never fabricated here) ---
    approval_ref = gate.get("owner_approval_ref")
    if not approval_ref:
        blockers.append("jar15_approval_not_recorded")
    else:
        approval_path = _safe_ref(root, approval_ref)
        if approval_path is None:
            blockers.append("jar15_approval_ref_invalid")
        elif not approval_path.exists():
            blockers.append("jar15_approval_missing")
        else:
            try:
                approval = _load(approval_path)
            except (OSError, json.JSONDecodeError):
                blockers.append("jar15_approval_invalid_json")
            else:
                if approval.get("schema_version") != "aftergraph.system-one-calibration-approval/0.1":
                    blockers.append("jar15_approval_schema_invalid")
                if approval.get("experiment_id") != "JAR-EXP-0015":
                    blockers.append("jar15_approval_experiment_mismatch")
                if approval.get("approved") is not True:
                    blockers.append("jar15_approval_not_granted")
                if approval.get("network_calls_authorized") is not True:
                    blockers.append("jar15_approval_network_scope_missing")
                if approval.get("requested_typesafe_model") != requested_model:
                    blockers.append("jar15_approval_model_mismatch")
                if approval.get("calibration_manifest_sha256") != manifest_pin:
                    blockers.append("jar15_approval_manifest_mismatch")
                if approval.get("max_provider_calls") != max_calls:
                    blockers.append("jar15_approval_call_ceiling_mismatch")
                if approval.get("max_cost_usd") != max_cost:
                    blockers.append("jar15_approval_cost_ceiling_mismatch")
                _valid_attribution(approval, blockers, "jar15_approval")

    if gate.get("network_calls_authorized") is not True:
        blockers.append("jar15_network_calls_not_authorized")

    return Jar15CalibrationPreflightResult(
        "READY_TO_CALIBRATE" if not blockers else "NO_GO",
        tuple(blockers),
        maximum_calls=_int(max_calls),
        maximum_cost_usd=_positive_number(max_cost),
        requested_model=requested_model
        if isinstance(requested_model, str) and requested_model.strip()
        else None,
    )