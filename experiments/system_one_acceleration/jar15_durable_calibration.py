"""Durable A/B/C calibration execution for JAR-EXP-0015."""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import os

from .adapter import normalize_typesafe_answer, returned_model
from .calibration import CalibrationDecision, select_threshold
from .calibration_runner import (
    CalibrationObservation,
    CalibrationRunError,
    CalibrationRunResult,
    _answer_from_response,
    _predict,
    _usage_from_response,
)
from .client import build_sdk_questions, invoke_system_one
from .corpus import CalibrationCase
from .cost_guard import CostReservation
from .jar15_cost_guard import JAR15StageCostGuard
from .protocol import effective_confidence


class JAR15CheckpointError(RuntimeError):
    pass


def jar15_calibration_checkpoint_path() -> Path:
    return (
        Path.home()
        / ".aftergraph"
        / "research"
        / "jar-exp-0015"
        / "abc-calibration-checkpoint-v01.json"
    )


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    with open(tmp, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _load_checkpoint(path: Path, *, run_id: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": "jar-exp-0015.abc-calibration-checkpoint/0.1",
            "experiment_id": "JAR-EXP-0015",
            "stage": "A_B_C_ORIGINAL_CONTRACT_CALIBRATION",
            "run_id": run_id,
            "observations": {},
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JAR15CheckpointError("checkpoint unreadable") from exc
    if value.get("schema_version") != "jar-exp-0015.abc-calibration-checkpoint/0.1":
        raise JAR15CheckpointError("checkpoint schema mismatch")
    if value.get("experiment_id") != "JAR-EXP-0015":
        raise JAR15CheckpointError("checkpoint experiment mismatch")
    if value.get("stage") != "A_B_C_ORIGINAL_CONTRACT_CALIBRATION":
        raise JAR15CheckpointError("checkpoint stage mismatch")
    if value.get("run_id") != run_id:
        raise JAR15CheckpointError("checkpoint run mismatch")
    if not isinstance(value.get("observations"), dict):
        raise JAR15CheckpointError("checkpoint observations invalid")
    return value


def _observation_from_dict(value: Mapping[str, Any]) -> CalibrationObservation:
    required = {
        "case_id", "decision_type", "expected", "predicted", "correct", "critical",
        "effective_confidence", "returned_model", "latency_ms", "input_tokens",
        "output_tokens",
    }
    if set(value) != required:
        raise JAR15CheckpointError("checkpoint observation shape mismatch")
    return CalibrationObservation(**dict(value))


def run_jar15_abc_calibration(
    *,
    client: Any,
    sdk: Any,
    requested_model: str,
    contracts: Mapping[str, Mapping[str, Any]],
    cases: Sequence[CalibrationCase],
    cost_guard: JAR15StageCostGuard,
    checkpoint_path: Path | None = None,
) -> CalibrationRunResult:
    if len(cases) != 1952:
        raise CalibrationRunError("A/B/C calibration requires exactly 1,952 cases")
    if set(case.case_id for case in cases) != cost_guard.allowed_case_ids:
        raise CalibrationRunError("case set does not equal frozen calibration split")

    path = Path(checkpoint_path or jar15_calibration_checkpoint_path())
    checkpoint = _load_checkpoint(path, run_id=cost_guard.ledger.run_id)
    stored = checkpoint["observations"]
    allowed = {case.case_id for case in cases}
    if set(stored) - allowed:
        raise JAR15CheckpointError("checkpoint contains cases outside frozen calibration split")

    observations: list[CalibrationObservation] = []

    for case in cases:
        if case.decision_type not in contracts:
            raise CalibrationRunError(f"{case.case_id}: missing original contract")

        record = cost_guard.ledger.reservation_record(case.case_id)
        saved = stored.get(case.case_id)

        if saved is not None:
            if not isinstance(saved, dict):
                raise JAR15CheckpointError(f"{case.case_id}: checkpoint row invalid")
            request_sha = saved.get("request_sha256")
            raw = saved.get("observation")
            if not isinstance(request_sha, str) or not isinstance(raw, dict):
                raise JAR15CheckpointError(f"{case.case_id}: checkpoint binding invalid")
            observation = _observation_from_dict(raw)
            if (
                observation.case_id != case.case_id
                or observation.decision_type != case.decision_type
                or observation.expected != case.expected
                or observation.critical != case.critical
            ):
                raise JAR15CheckpointError(f"{case.case_id}: checkpoint case mismatch")
            if record is None or record["request_sha256"] != request_sha:
                raise JAR15CheckpointError(f"{case.case_id}: checkpoint/ledger mismatch")
            if record["status"] == "TRANSPORT_STARTED":
                reservation = CostReservation(
                    request_id=case.case_id,
                    request_sha256=request_sha,
                    reserved_microusd=int(record["reserved_microusd"]),
                    projected_state={},
                    contract={},
                )
                cost_guard.complete_request(
                    reservation, actual_input_tokens=observation.input_tokens
                )
            elif record["status"] != "COMPLETED":
                raise JAR15CheckpointError(
                    f"{case.case_id}: invalid ledger state {record['status']}"
                )
            observations.append(observation)
            continue

        if record is not None:
            if record["status"] == "TRANSPORT_STARTED":
                raise JAR15CheckpointError(
                    f"{case.case_id}: ambiguous prior transport without durable observation"
                )
            if record["status"] != "RESERVED":
                raise JAR15CheckpointError(
                    f"{case.case_id}: ledger state without durable observation: {record['status']}"
                )

        reservation = cost_guard.reserve_request(
            request_id=case.case_id,
            decision_type=case.decision_type,
            state=case.state,
            contract=contracts[case.decision_type],
            requested_model=requested_model,
        )
        questions = build_sdk_questions(
            {case.decision_type: reservation.contract}, sdk=sdk
        )
        cost_guard.begin_transport(reservation)
        response, latency_ms = invoke_system_one(
            client=client,
            state=reservation.projected_state,
            questions=questions,
            requested_model=requested_model,
            sdk=sdk,
        )
        model = returned_model(response)
        if model != requested_model:
            raise CalibrationRunError(
                f"{case.case_id}: returned model {model!r} != pinned {requested_model!r}"
            )
        normalized = normalize_typesafe_answer(
            _answer_from_response(response, case.decision_type)
        )
        input_tokens, output_tokens = _usage_from_response(response)
        confidence = effective_confidence(
            answer_kind=normalized["kind"],
            answer_value=normalized["value"],
            reported_confidence=normalized["confidence"],
        )
        if confidence is None:
            raise CalibrationRunError(f"{case.case_id}: no usable effective confidence")
        predicted = _predict(normalized)
        observation = CalibrationObservation(
            case_id=case.case_id,
            decision_type=case.decision_type,
            expected=case.expected,
            predicted=predicted,
            correct=predicted == case.expected,
            critical=case.critical,
            effective_confidence=confidence,
            returned_model=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        stored[case.case_id] = {
            "request_sha256": reservation.request_sha256,
            "observation": asdict(observation),
        }
        _atomic_write(path, checkpoint)
        cost_guard.complete_request(reservation, actual_input_tokens=input_tokens)
        observations.append(observation)

    if len(observations) != 1952:
        raise JAR15CheckpointError("calibration did not cover all frozen cases")
    if {row.returned_model for row in observations} != {requested_model}:
        raise CalibrationRunError("returned model drift within calibration")

    threshold = select_threshold(
        (
            CalibrationDecision(
                effective_confidence=row.effective_confidence,
                correct=row.correct,
                critical=row.critical,
            )
            for row in observations
        ),
        minimum_coverage=0.30,
        maximum_wilson_error=0.05,
    )
    return CalibrationRunResult(
        requested_model=requested_model,
        returned_model=requested_model,
        observations=tuple(observations),
        threshold=threshold,
        provider_calls=len(observations),
        input_tokens=sum(row.input_tokens for row in observations),
        output_tokens=sum(row.output_tokens for row in observations),
    )
