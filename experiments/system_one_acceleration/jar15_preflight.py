"""Zero-network stage preflight for JAR-EXP-0015."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .jar15_cost_guard import load_jar15_pricing_spec


@dataclass(frozen=True)
class JAR15StagePreflight:
    decision: str
    blockers: tuple[str, ...]
    requested_model: str | None
    maximum_calls: int | None
    maximum_cost_usd: float | None


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def evaluate_jar15_stage_preflight(root: Path, *, stage: str) -> JAR15StagePreflight:
    if stage not in {"calibration", "holdout"}:
        raise ValueError("stage must be calibration or holdout")
    root = Path(root)
    blockers: list[str] = []

    active_path = root / "data" / "jar_exp_0015_active_protocol.json"
    protocol_path = root / "data" / "jar_exp_0015_protocol_v04.json"
    dataset_path = root / "data" / "jar_exp_0015_dataset_v03.json"
    pricing_path = root / "data" / "jar_exp_0015_typesafe_pricing_v01.json"
    gate_path = root / "data" / (
        "jar_exp_0015_calibration_gate_v01.json"
        if stage == "calibration"
        else "jar_exp_0015_holdout_gate_v01.json"
    )

    try:
        active = _load(active_path)
        protocol = _load(protocol_path)
        gate = _load(gate_path)
        spec = load_jar15_pricing_spec(pricing_path)
    except Exception:
        return JAR15StagePreflight(
            "NO_GO", ("stage_inputs_unavailable_or_invalid",), None, None, None
        )

    if active.get("active_protocol_ref") != "data/jar_exp_0015_protocol_v04.json":
        blockers.append("active_protocol_mismatch")
    if protocol.get("schema_version") != "jar-exp-0015.protocol/0.4":
        blockers.append("protocol_version_mismatch")
    if protocol.get("network_calls_authorized") is not False:
        blockers.append("protocol_must_remain_non_authorizing")

    dataset_sha = _sha256(dataset_path)
    if dataset_sha != protocol["dataset"].get("dataset_sha256"):
        blockers.append("dataset_protocol_hash_mismatch")
    if dataset_sha != gate.get("dataset_sha256"):
        blockers.append("dataset_gate_hash_mismatch")

    if gate.get("active_protocol_ref") != "data/jar_exp_0015_protocol_v04.json":
        blockers.append("gate_protocol_mismatch")
    if gate.get("requested_model") != spec.model_id:
        blockers.append("gate_model_mismatch")
    if gate.get("sdk_retries_allowed") is not False:
        blockers.append("sdk_retries_not_disabled")

    max_calls = gate.get("max_provider_calls")
    max_cost = gate.get("max_cost_usd")
    expected_calls = int(protocol["dataset"][
        "total_calibration" if stage == "calibration" else "total_holdout"
    ])
    if max_calls != expected_calls:
        blockers.append("provider_call_ceiling_mismatch")
    worst_case = expected_calls * spec.max_request_cost_microusd
    if not isinstance(max_cost, (int, float)) or max_cost * 1_000_000 < worst_case:
        blockers.append("cost_hard_stop_insufficient")

    if stage == "calibration":
        if gate.get("semantic_review_ref") is None:
            blockers.append("calibration_semantic_review_not_recorded")
        if gate.get("owner_approval_ref") is None:
            blockers.append("calibration_owner_approval_not_recorded")
        if gate.get("network_calls_authorized") is not True:
            blockers.append("calibration_network_calls_not_authorized")
        decision_name = "READY_TO_CALIBRATE"
    else:
        if gate.get("frozen_policy_ref") is None or gate.get("frozen_policy_sha256") is None:
            blockers.append("holdout_frozen_policy_not_recorded")
        if gate.get("semantic_review_ref") is None:
            blockers.append("holdout_semantic_review_not_recorded")
        if gate.get("owner_approval_ref") is None:
            blockers.append("holdout_owner_approval_not_recorded")
        if gate.get("holdout_evaluation_authorized") is not True:
            blockers.append("holdout_evaluation_not_authorized")
        if gate.get("network_calls_authorized") is not True:
            blockers.append("holdout_network_calls_not_authorized")
        decision_name = "READY_TO_HOLDOUT"

    return JAR15StagePreflight(
        decision_name if not blockers else "NO_GO",
        tuple(blockers),
        spec.model_id,
        max_calls if isinstance(max_calls, int) and not isinstance(max_calls, bool) else None,
        float(max_cost) if isinstance(max_cost, (int, float)) and not isinstance(max_cost, bool) else None,
    )
