from experiments.institutional_containment.power import (
    conservative_two_proportion_n_per_condition,
    planned_total_runs,
)


def test_power_plan_is_deterministic_and_positive():
    n1 = conservative_two_proportion_n_per_condition()
    n2 = conservative_two_proportion_n_per_condition()
    assert n1 == n2
    assert n1 > 0


def test_smaller_effect_requires_more_samples():
    n_10 = conservative_two_proportion_n_per_condition(minimum_detectable_difference=0.10)
    n_05 = conservative_two_proportion_n_per_condition(minimum_detectable_difference=0.05)
    assert n_05 > n_10


def test_stricter_alpha_requires_more_samples():
    n_05 = conservative_two_proportion_n_per_condition(alpha=0.05)
    n_01 = conservative_two_proportion_n_per_condition(alpha=0.01)
    assert n_01 > n_05


def test_planned_total_runs_balances_replicates_across_scenarios():
    assert planned_total_runs(scenarios=6, conditions=7, n_per_condition=13) == 126
