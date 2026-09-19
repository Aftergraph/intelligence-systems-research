"""Pre-registered threshold selection for JAR-EXP-0014."""

from dataclasses import dataclass
from math import sqrt
from typing import Iterable


@dataclass(frozen=True)
class CalibrationDecision:
    effective_confidence: float
    correct: bool
    critical: bool = False


@dataclass(frozen=True)
class ThresholdResult:
    threshold: float | None
    accepted: int
    total: int
    coverage: float
    errors: int
    error_rate: float | None
    wilson_upper: float | None
    critical_errors: int
    feasible: bool


def wilson_upper(errors: int, n: int, z: float = 1.959963984540054) -> float | None:
    if n <= 0:
        return None
    if errors < 0 or errors > n:
        raise ValueError("errors must be within [0, n]")
    p = errors / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p + z2 / (2.0 * n)
    spread = z * sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n)
    return min(1.0, (centre + spread) / denom)


def evaluate_threshold(
    rows: Iterable[CalibrationDecision],
    threshold: float,
    *,
    minimum_coverage: float = 0.30,
    maximum_wilson_error: float = 0.05,
) -> ThresholdResult:
    rows = tuple(rows)
    if not rows:
        raise ValueError("calibration rows are required")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be within [0, 1]")
    for row in rows:
        if not 0.0 <= row.effective_confidence <= 1.0:
            raise ValueError("effective confidence must be within [0, 1]")

    accepted_rows = tuple(
        row for row in rows if row.effective_confidence >= threshold
    )
    accepted = len(accepted_rows)
    total = len(rows)
    coverage = accepted / total
    errors = sum(not row.correct for row in accepted_rows)
    critical_errors = sum(
        row.critical and not row.correct for row in accepted_rows
    )
    rate = errors / accepted if accepted else None
    upper = wilson_upper(errors, accepted)
    feasible = (
        coverage >= minimum_coverage
        and upper is not None
        and upper <= maximum_wilson_error
        and critical_errors == 0
    )
    return ThresholdResult(
        threshold=threshold,
        accepted=accepted,
        total=total,
        coverage=coverage,
        errors=errors,
        error_rate=rate,
        wilson_upper=upper,
        critical_errors=critical_errors,
        feasible=feasible,
    )


def select_threshold(
    rows: Iterable[CalibrationDecision],
    *,
    minimum_coverage: float = 0.30,
    maximum_wilson_error: float = 0.05,
) -> ThresholdResult:
    rows = tuple(rows)
    if not rows:
        raise ValueError("calibration rows are required")
    candidates = sorted(
        {0.0, 1.0, *(float(row.effective_confidence) for row in rows)}
    )
    evaluated = [
        evaluate_threshold(
            rows,
            threshold,
            minimum_coverage=minimum_coverage,
            maximum_wilson_error=maximum_wilson_error,
        )
        for threshold in candidates
    ]
    feasible = [result for result in evaluated if result.feasible]
    if not feasible:
        return ThresholdResult(
            threshold=None,
            accepted=0,
            total=len(rows),
            coverage=0.0,
            errors=0,
            error_rate=None,
            wilson_upper=None,
            critical_errors=0,
            feasible=False,
        )
    # Lowest feasible threshold maximizes accepted coverage by preregistration.
    return min(feasible, key=lambda result: result.threshold)
