import pytest

from experiments.runtime_acceleration.analysis.analyze import (
    bootstrap_median_difference,
    newcombe_difference_interval,
    paired_bootstrap_median_reduction,
    wilson_interval,
)


def test_wilson_interval_is_bounded():
    low, high = wilson_interval(95, 100)
    assert 0.0 <= low <= 0.95 <= high <= 1.0


def test_bootstrap_median_difference_is_seeded():
    a = bootstrap_median_difference([10, 11, 12, 13], [7, 8, 9, 10], seed=13, resamples=200)
    b = bootstrap_median_difference([10, 11, 12, 13], [7, 8, 9, 10], seed=13, resamples=200)
    assert a == b
    assert a["observed_difference"] == -3.0
    assert a["ci_low"] <= a["observed_difference"] <= a["ci_high"]


def test_paired_bootstrap_median_reduction_is_seeded_and_preserves_pairs():
    control = [100.0, 200.0, 300.0, 400.0]
    treatment = [90.0, 180.0, 270.0, 360.0]
    a = paired_bootstrap_median_reduction(control, treatment, seed=130013, resamples=500)
    b = paired_bootstrap_median_reduction(control, treatment, seed=130013, resamples=500)
    assert a == b
    assert a["method"] == "paired_percentile_bootstrap"
    assert a["observed_reduction"] == pytest.approx(0.10)
    assert a["ci_low"] == pytest.approx(0.10)
    assert a["ci_high"] == pytest.approx(0.10)


def test_paired_bootstrap_requires_equal_pair_counts():
    with pytest.raises(ValueError, match="equal length"):
        paired_bootstrap_median_reduction([100.0, 200.0], [90.0], seed=130013, resamples=100)


def test_newcombe_difference_interval_supports_five_point_noninferiority_at_perfect_success():
    low, high = newcombe_difference_interval(100, 100, 100, 100)
    assert low > -0.05
    assert low <= 0.0 <= high
