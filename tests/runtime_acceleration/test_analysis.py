from experiments.runtime_acceleration.analysis.analyze import bootstrap_median_difference, wilson_interval


def test_wilson_interval_is_bounded():
    low, high = wilson_interval(95, 100)
    assert 0.0 <= low <= 0.95 <= high <= 1.0


def test_bootstrap_median_difference_is_seeded():
    a = bootstrap_median_difference([10, 11, 12, 13], [7, 8, 9, 10], seed=13, resamples=200)
    b = bootstrap_median_difference([10, 11, 12, 13], [7, 8, 9, 10], seed=13, resamples=200)
    assert a == b
    assert a["observed_difference"] == -3.0
    assert a["ci_low"] <= a["observed_difference"] <= a["ci_high"]
