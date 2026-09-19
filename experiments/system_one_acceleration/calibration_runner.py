"""Bounded calibration runner for JAR-EXP-0014.

Network behavior is entirely delegated to the injected client. This runner adds
no retries, writes no files, and never authorizes consequential actions.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .adapter import normalize_typesafe_answer, returned_model
from .calibration import CalibrationDecision, ThresholdResult, select_threshold
from .client import build_sdk_questions, invoke_system_one
from .corpus import CalibrationCase
from .protocol import effective_confidence


class CalibrationRunError(RuntimeError):
    pass


@dataclass(frozen=True)
class CalibrationObservation:
    case_id: str
    decision_type: str
    expected: Any
    predicted: Any
    correct: bool
    critical: bool
    effective_confidence: float
    returned_model: str
    latency_ms: float


@dataclass(frozen=True)
class CalibrationRunResult:
    requested_model: str
    returned_model: str
    observations: tuple[CalibrationObservation, ...]
    threshold: ThresholdResult
    provider_calls: int


def _answer_from_response(response: Any, key: str) -> Any:
    answers = getattr(response, "answers", None)
    if answers is None and isinstance(response, Mapping):
        answers = response.get("answers")
    if not isinstance(answers, Mapping) or key not in answers:
        raise CalibrationRunError(f"provider response missing answer for {key}")
    return answers[key]


def _predict(normalized: Mapping[str, Any]) -> Any:
    kind = normalized["kind"]
    if kind == "noul":
        return normalized["value"] >= 0.5
    if kind == "choice":
        return normalized["value"]
    if kind == "score":
        distribution = normalized["distribution"]
        if not distribution:
            raise CalibrationRunError("score distribution missing")
        maximum = max(distribution.values())
        winners = [key for key, value in distribution.items() if value == maximum]
        if len(winners) != 1:
            raise CalibrationRunError("score distribution has an ambiguous maximum")
        try:
            return int(winners[0])
        except ValueError as exc:
            raise CalibrationRunError("score level is not an integer") from exc
    raise CalibrationRunError(f"unsupported normalized answer kind: {kind}")


def run_calibration(
    *,
    client: Any,
    sdk: Any,
    requested_model: str,
    contracts: Mapping[str, Mapping[str, Any]],
    cases: Sequence[CalibrationCase],
    maximum_calls: int,
) -> CalibrationRunResult:
    if maximum_calls <= 0:
        raise ValueError("maximum_calls must be positive")
    if len(cases) > maximum_calls:
        raise CalibrationRunError("calibration exceeds provider-call ceiling")

    observations: list[CalibrationObservation] = []
    returned_models: set[str] = set()

    for case in cases:
        if case.decision_type not in contracts:
            raise CalibrationRunError(
                f"{case.case_id}: missing frozen contract {case.decision_type}"
            )
        questions = build_sdk_questions(
            {case.decision_type: contracts[case.decision_type]},
            sdk=sdk,
        )
        response, latency_ms = invoke_system_one(
            client=client,
            state=case.state,
            questions=questions,
            requested_model=requested_model,
        )
        model = returned_model(response)
        returned_models.add(model)

        normalized = normalize_typesafe_answer(
            _answer_from_response(response, case.decision_type)
        )
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
        observations.append(
            CalibrationObservation(
                case_id=case.case_id,
                decision_type=case.decision_type,
                expected=case.expected,
                predicted=predicted,
                correct=predicted == case.expected,
                critical=case.critical,
                effective_confidence=confidence,
                returned_model=model,
                latency_ms=latency_ms,
            )
        )

    if len(returned_models) != 1:
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
        returned_model=next(iter(returned_models)),
        observations=tuple(observations),
        threshold=threshold,
        provider_calls=len(observations),
    )
