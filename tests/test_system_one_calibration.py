import pytest

from experiments.system_one_acceleration.calibration import (
    CalibrationDecision,
    evaluate_threshold,
    select_threshold,
    wilson_upper,
)


def test_wilson_upper_is_conservative_for_zero_errors():
    assert wilson_upper(0, 100) > 0.0
    assert wilson_upper(0, 100) < 0.05


def test_threshold_requires_coverage_and_wilson_bound():
    rows = [CalibrationDecision(0.99, True) for _ in range(100)]
    result = evaluate_threshold(rows, 0.99)
    assert result.feasible is True
    sparse = evaluate_threshold(rows, 1.0)
    assert sparse.accepted == 0
    assert sparse.feasible is False


def test_any_accepted_critical_error_makes_threshold_infeasible():
    rows = [CalibrationDecision(0.99, True) for _ in range(99)]
    rows.append(CalibrationDecision(0.99, False, critical=True))
    result = evaluate_threshold(rows, 0.99)
    assert result.critical_errors == 1
    assert result.feasible is False


def test_selector_chooses_lowest_feasible_threshold_for_max_coverage():
    rows = (
        [CalibrationDecision(0.95, True) for _ in range(100)]
        + [CalibrationDecision(0.80, True) for _ in range(100)]
        + [CalibrationDecision(0.60, False) for _ in range(20)]
    )
    result = select_threshold(rows)
    assert result.feasible is True
    assert result.threshold == 0.80
    assert result.accepted == 200


def test_selector_returns_no_threshold_when_quality_gate_cannot_be_met():
    rows = [
        CalibrationDecision(0.99, index % 3 != 0, critical=(index == 0))
        for index in range(128)
    ]
    result = select_threshold(rows)
    assert result.feasible is False
    assert result.threshold is None


def test_invalid_confidence_fails_closed():
    with pytest.raises(ValueError):
        evaluate_threshold([CalibrationDecision(1.1, True)], 0.9)
