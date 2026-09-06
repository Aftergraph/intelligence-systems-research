from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DifferentialResult:
    equal: bool
    classification: str
    details: dict


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize(item) for item in value)
    return value


def compare_observable(control: Any, treatment: Any) -> DifferentialResult:
    """Compare treatment output against control without forgiving mismatches."""
    if isinstance(control, dict) and isinstance(treatment, dict):
        control_error = control.get("error_class")
        treatment_error = treatment.get("error_class")
        if control_error != treatment_error:
            return DifferentialResult(
                equal=False,
                classification="ERROR_CLASS_MISMATCH",
                details={"control_error_class": control_error, "treatment_error_class": treatment_error},
            )

    normalized_control = _normalize(control)
    normalized_treatment = _normalize(treatment)
    if normalized_control == normalized_treatment:
        return DifferentialResult(True, "EQUIVALENT", {})

    return DifferentialResult(
        equal=False,
        classification="SEMANTIC_MISMATCH",
        details={"control": normalized_control, "treatment": normalized_treatment},
    )
