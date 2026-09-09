import json
from pathlib import Path

from experiments.institutional_containment.power import (
    build_frozen_power_plan,
    conservative_two_proportion_n_per_condition,
    planned_total_runs,
)


POWER_PLAN = Path("data/study012_power_plan.json")


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


def test_frozen_power_plan_counts_domains_in_pairing_math():
    plan = build_frozen_power_plan(
        domains=3,
        scenarios_per_domain=10,
        conditions=7,
    )
    assert plan["planning_method"] == "conservative_independent_two_proportion_upper_bound_v1"
    assert plan["outcome_blind"] is True
    assert plan["n_per_condition_required"] == 577
    assert plan["pairs_per_replicate"] == 30
    assert plan["replicates"] == 20
    assert plan["observations_per_condition"] == 600
    assert plan["total_runs"] == 4200


def test_frozen_power_plan_artifact_matches_code_and_contains_no_observed_outcomes():
    frozen = json.loads(POWER_PLAN.read_text(encoding="utf-8"))
    recomputed = build_frozen_power_plan(
        domains=frozen["domains"],
        scenarios_per_domain=frozen["scenarios_per_domain"],
        conditions=frozen["conditions"],
        baseline_rate=frozen["baseline_rate"],
        minimum_detectable_difference=frozen["minimum_detectable_difference"],
        alpha=frozen["alpha"],
        power=frozen["power"],
    )
    assert frozen == recomputed
    forbidden = {
        "observed_rate",
        "observed_effect",
        "pilot_rate",
        "condition_outcomes",
        "winner",
    }
    assert forbidden.isdisjoint(frozen)
