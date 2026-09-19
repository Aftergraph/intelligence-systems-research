"""Durable/resumable live calibration runner for JAR-EXP-0014.

Each completed provider response is checkpointed atomically before the budget ledger
is marked COMPLETED. On restart, checkpoint + ledger state are reconciled without
replaying a provider call. A TRANSPORT_STARTED row without a checkpoint is ambiguous
and fails closed.
"""

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
from .cost_guard import CostReservation, PreRequestCostGuard
from .protocol import effective_confidence


class CalibrationCheckpointError(RuntimeError):
    pass


def calibration_checkpoint_path() -> Path:
    return (
        Path.home()
        / ".aftergraph"
        / "research"
        / "jar-exp-0014"
        / "calibration-checkpoint-v01.json"
    )


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    with open(tmp, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _load_checkpoint(path: Path, *, run_id: str) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": "jar-exp-0014.calibration-checkpoint/0.1", "run_id": run_id, "observations": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CalibrationCheckpointError("calibration checkpoint unreadable") from exc
    if value.get("schema_version") != "jar-exp-0014.calibration-checkpoint/0.1":
        raise CalibrationCheckpointError("calibration checkpoint schema mismatch")
    if value.get("run_id") != run_id:
        raise CalibrationCheckpointError("calibration checkpoint run mismatch")
    observations = value.get("observations")
    if not isinstance(observations, dict):
        raise CalibrationCheckpointError("calibration checkpoint observations invalid")
    return value


def _observation_from_dict(value: Mapping[str, Any]) -> CalibrationObservation:
    required = {
        "case_id", "decision_type", "expected", "predicted", "correct", "critical",
        "effective_confidence", "returned_model", "latency_ms", "input_tokens", "output_tokens",
    }
    if set(value) != required:
        raise CalibrationCheckpointError("checkpoint observation shape mismatch")
    return CalibrationObservation(**dict(value))


def run_durable_calibration(
    *,
    client: Any,
    sdk: Any,
    requested_model: str,
    contracts: Mapping[str, Mapping[str, Any]],
    cases: Sequence[CalibrationCase],
    maximum_calls: int,
    cost_guard: PreRequestCostGuard,
    checkpoint_path: Path | None = None,
) -> CalibrationRunResult:
    if maximum_calls <= 0:
        raise ValueError("maximum_calls must be positive")
    if len(cases) > maximum_calls:
        raise CalibrationRunError("calibration exceeds provider-call ceiling")

    path = Path(checkpoint_path or calibration_checkpoint_path())
    run_id = cost_guard.ledger.run_id
    checkpoint = _load_checkpoint(path, run_id=run_id)
    stored = checkpoint["observations"]
    case_ids = {case.case_id for case in cases}
    unknown = set(stored) - case_ids
    if unknown:
        raise CalibrationCheckpointError(
            "checkpoint contains cases outside frozen corpus: " + ", ".join(sorted(unknown))
        )

    observations: list[CalibrationObservation] = []

    for case in cases:
        if case.decision_type not in contracts:
            raise CalibrationRunError(
                f"{case.case_id}: missing frozen contract {case.decision_type}"
            )

        record = cost_guard.ledger.reservation_record(case.case_id)
        saved = stored.get(case.case_id)

        if saved is not None:
            if not isinstance(saved, dict):
                raise CalibrationCheckpointError(f"{case.case_id}: checkpoint row invalid")
            request_sha = saved.get("request_sha256")
            observation_raw = saved.get("observation")
            if not isinstance(request_sha, str) or not isinstance(observation_raw, dict):
                raise CalibrationCheckpointError(f"{case.case_id}: checkpoint binding invalid")
            observation = _observation_from_dict(observation_raw)
            if (
                observation.case_id != case.case_id
                or observation.decision_type != case.decision_type
                or observation.expected != case.expected
                or observation.critical != case.critical
            ):
                raise CalibrationCheckpointError(
                    f"{case.case_id}: checkpoint does not match frozen case"
                )
            if record is None or record["request_sha256"] != request_sha:
                raise CalibrationCheckpointError(
                    f"{case.case_id}: checkpoint/ledger binding mismatch"
                )
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
                raise CalibrationCheckpointError(
                    f"{case.case_id}: checkpoint exists in invalid ledger state {record['status']}"
                )
            observations.append(observation)
            continue

        if record is not None:
            if record["status"] == "RESERVED":
                pass
            elif record["status"] == "TRANSPORT_STARTED":
                raise CalibrationCheckpointError(
                    f"{case.case_id}: ambiguous prior transport without durable observation"
                )
            else:
                raise CalibrationCheckpointError(
                    f"{case.case_id}: ledger has {record['status']} without durable observation"
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
            raise CalibrationRunError(
                f"{case.case_id}: normalized answer has no usable certainty"
            )
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
        _atomic_write_json(path, checkpoint)
        cost_guard.complete_request(reservation, actual_input_tokens=input_tokens)
        observations.append(observation)

    if len(observations) != len(cases):
        raise CalibrationCheckpointError("durable calibration did not cover frozen corpus")

    returned_models = {row.returned_model for row in observations}
    if returned_models != {requested_model}:
        raise CalibrationRunError(
            f"returned model drift within calibration run: {sorted(returned_models)}"
        )

    threshold = select_threshold(
        CalibrationDecision(
            effective_confidence=row.effective_confidence,
            correct=row.correct,
            critical=row.critical,
        )
        for row in observations
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
